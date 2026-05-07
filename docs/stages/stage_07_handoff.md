# Stage 07 — Hand-off, Routing e Transfer Logic

_Fonte canônica: [`../platform_technical_spec.md`](../platform_technical_spec.md). Este stage reorganiza o conteúdo técnico sem substituir a especificação completa._

## Objetivo

Definir vínculos entre agentes, tools fantasma, decisão reativa/proativa, router classifier e contrato sanitizado de transferência.

## Tabela Relevante

```sql
-- Vínculos de hand-off entre instâncias (Agente Y pode transferir para Agente X)
CREATE TABLE agent_links (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  source_instance_id  UUID NOT NULL REFERENCES agent_instances(id),  -- quem transfere
  target_instance_id  UUID NOT NULL REFERENCES agent_instances(id),  -- para quem transfere
  transfer_tool_name  TEXT NOT NULL,    -- ex: "transfer_to_finance_agent"
  trigger_description TEXT NOT NULL,   -- "Use quando o cliente quiser falar sobre faturas..."
  transfer_mode   TEXT NOT NULL DEFAULT 'llm_decision',  -- llm_decision | router_classifier
  is_enabled      BOOLEAN NOT NULL DEFAULT true,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(source_instance_id, target_instance_id)
);
```

## 6. Orquestração de Agentes e Hand-off

### Conceito

Para o Agente Y transferir para o Agente X, o Agente X é exposto ao LLM do Agente Y como uma **tool fantasma**. O LLM do Agente Y decide usar essa tool baseado na sua descrição, e a execução do Agente Y é interrompida para iniciar o Agente X com um **Resumo de Hand-off**.

O Agente X não recebe o histórico bruto completo. Ele recebe:

- Um resumo objetivo do problema, intenção do usuário e estado atual da conversa.
- A razão estruturada da transferência (`reason`) enviada pela tool fantasma.
- As últimas `N` mensagens conversacionais relevantes, sem mensagens `tool_call`, `tool_result` ou instruções internas do agente anterior.
- Metadados seguros da sessão (`tenant_id`, `session_id`, `source_instance_id`, `target_instance_id`).

Esse contrato evita vazamento de instruções e schemas de ferramentas que só existem no Agente Y, reduz pressão no limite de tokens e torna transferências encadeadas previsíveis.

### Configuração no dashboard

No dashboard, o Tenant Admin acessa as configurações de uma instância e, na seção **"Agentes Vinculados"**, seleciona qual instância pode receber transferências e define a descrição de quando transferir.

```
Instância: Agente de Triagem
└── Agentes Vinculados
    ├── [+] Especialista Financeiro
    │       Tool name: transfer_to_finance_agent
    │       Quando usar: "Use quando o cliente quiser falar sobre
    │                     faturas, cobranças ou pagamentos."
    │       Modo: Decisão do LLM
    │
    └── [+] Suporte Técnico
            Tool name: transfer_to_tech_support
            Quando usar: "Use quando o cliente reportar bugs,
                          erros ou problemas com o produto."
            Modo: Router Classifier (pré-triagem)
```

### Dois modos de hand-off

**Modo A — Decisão do LLM (Reativo):**

O agente Y lê a mensagem, reconhece que existe uma tool para transferir ao Agente X e decide usá-la. É o modo padrão — flexível e não requer configuração adicional.

```
Usuário: "Tenho uma cobrança duplicada no meu cartão"
   ↓
Agente Y (Triagem) recebe mensagem
   ↓
LLM vê tool "transfer_to_finance_agent" no prompt
   ↓
LLM chama a tool com reason="cobrança duplicada"
   ↓
handoff_node interrompe Agente Y, cria resumo e inicia Agente X
```

**Modo B — Router Classifier (Proativo):**

Antes de chegar ao Agente Y, um modelo menor e mais barato lê a mensagem, consulta as regras de vínculos do banco e já direciona para o Agente correto. Reduz latência em fluxos com alta previsibilidade.

```
Usuário: "Tenho uma cobrança duplicada no meu cartão"
   ↓
Router lê mensagem + regras de agent_links
   ↓
Classifica: "finance" → instance_id do Agente Financeiro
   ↓
Execução vai diretamente para o Agente X
   ↓
(Agente Y nunca é invocado)
```

### Implementação do handoff_node

```python
# engine/nodes/handoff_node.py

async def handoff_node(state: AgentState, db: TenantDB) -> AgentState:
    call = state["pending_tool_calls"][0]
    tool_name = call["name"]

    # Resolve qual instância é o destino
    link = await db.get_link_by_tool_name(
        source_instance_id=state["instance_id"],
        transfer_tool_name=tool_name,
        tenant_id=state["tenant_id"],
    )

    if not link:
        # Tool fantasma não encontrada — retorna erro controlado
        return {**state, "tool_results": [{"error": f"Agente {tool_name} não disponível"}]}

    # Transfere apenas contexto sanitizado para o novo estado
    transfer_state = await RunBootstrap(db, redis).prepare(
        instance_id=link.target_instance_id,
        tenant_id=state["tenant_id"],
        session_id=state["session_id"],
    )
    transfer_state["handoff_summary"] = await HandoffSummarizer(db).summarize(
        messages=state["messages"],
        reason=call["args"]["reason"],
        source_instance_id=state["instance_id"],
        target_instance_id=link.target_instance_id,
    )
    transfer_state["messages"] = HandoffSanitizer.keep_recent_conversation(
        state["messages"],
        max_messages=8,
    )

    # Executa o agente destino
    result = await BASE_GRAPH.ainvoke(transfer_state)

    return {
        **state,
        "final_response": result.get("final_response"),
        "handoff_target": str(link.target_instance_id),
    }
```

### Contrato do Resumo de Hand-off

```python
# engine/handoff.py

class HandoffSummary(BaseModel):
    source_instance_id: UUID
    target_instance_id: UUID
    reason: str
    user_goal: str
    known_facts: list[str]
    open_questions: list[str]
    actions_already_taken: list[str]
    safety_notes: list[str] = []


class HandoffSanitizer:
    @staticmethod
    def keep_recent_conversation(messages: list[BaseMessage], max_messages: int = 8) -> list[BaseMessage]:
        allowed_roles = {"user", "assistant", "human", "ai"}
        clean = [
            m for m in messages
            if getattr(m, "type", getattr(m, "role", None)) in allowed_roles
            and not getattr(m, "tool_calls", None)
        ]
        return clean[-max_messages:]
```

### Router Classifier

```python
# engine/router.py

class IntentRouter:
    """
    Modelo leve de classificação que direciona mensagens para o agente
    correto antes da execução principal. Usado quando transfer_mode = 'router_classifier'.
    """

    async def route(self, message: str, tenant_id: str, default_instance_id: str) -> str:
        router_rules = await self.db.get_router_rules(tenant_id)

        if not router_rules:
            return default_instance_id

        # Chama modelo leve (ex: gpt-4.1-mini) com regras como contexto
        prompt = self._build_routing_prompt(message, router_rules)
        result = await self.llm.invoke(prompt)
        target_slug = result.strip()

        instance = await self.db.get_instance_by_slug(tenant_id, target_slug)
        return instance.id if instance else default_instance_id

    def _build_routing_prompt(self, message: str, rules: list) -> str:
        rules_text = "\n".join([
            f"- Se '{r.trigger_description}' → responda '{r.target_slug}'"
            for r in rules
        ])
        return (
            f"Com base nas regras abaixo, classifique para qual agente esta mensagem deve ir.\n"
            f"Responda APENAS com o slug do agente, sem explicação.\n\n"
            f"Regras:\n{rules_text}\n\n"
            f"Mensagem: {message}\n\n"
            f"Agente:"
        )
```

---
