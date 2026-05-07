# Visão Geral da Arquitetura

_Fonte canônica: [`platform_technical_spec.md`](platform_technical_spec.md). A especificação completa agora vive em /docs como referência final._

## Papel Deste Documento

Este arquivo é a visão macro navegável da plataforma. Ele não substitui a especificação completa nem os stages técnicos; ele conecta stack, runtime, segurança, infraestrutura, frontend e observabilidade em um único fluxo.

Para detalhes de implementação, use:

- [`platform_technical_spec.md`](platform_technical_spec.md): especificação completa, sem cortes.
- [`map.md`](map.md): roadmap e ordem de implementação.
- [`stages/stage_01_core_db.md`](stages/stage_01_core_db.md): schema PostgreSQL, RLS e multi-tenancy.
- [`stages/stage_02_auth_rbac.md`](stages/stage_02_auth_rbac.md): auth, JWT e permissões.
- [`stages/stage_03_registry.md`](stages/stage_03_registry.md): skills, tools, credenciais e Vault.
- [`stages/stage_04_engine.md`](stages/stage_04_engine.md): LangGraph, estado e Redis Lock.
- [`stages/stage_05_base_multitenant_workflows.md`](stages/stage_05_base_multitenant_workflows.md): workflows base multi-tenant, auth lifecycle, tenants, membros, convites, instancias e auditoria.
- [`stages/stage_05_prompts.md`](stages/stage_05_prompts.md): Prompt Sandwich, cache e sanitization.
- [`stages/stage_06_rag.md`](stages/stage_06_rag.md): Qdrant, indexação e retrieval.
- [`stages/stage_07_handoff.md`](stages/stage_07_handoff.md): hand-off e roteamento multiagente.
- [`stages/stage_08_channels.md`](stages/stage_08_channels.md): canais, WhatsApp, webhooks e Outbound Data Bridge.

## Stack

> Stack: LangGraph · FastAPI · Next.js · PostgreSQL · Qdrant · Redis · OpenTelemetry

## 1. Visão Geral e Princípios

### O que é a plataforma

Um SaaS multi-tenant de **Agent Registry**: existe um único agente base, completo e robusto, definido pela plataforma. Cada tenant cria **instâncias** desse agente e configura tudo via dashboard — identidade, skills ativas, ferramentas habilitadas, agentes vinculados para hand-off, RAG e canais de consumo.

Não há criação de agentes customizados por código nem múltiplos environments por tenant. O poder está na configuração dinâmica de cada instância: o prompt é montado em tempo real como um objeto composto, e as capacidades do agente refletem exatamente o que foi ativado no dashboard.

### Conceito central: o Prompt como Objeto Dinâmico

O prompt do sistema **não é um bloco de texto estático**. Ele é reconstruído a cada execução a partir de três camadas:

```
┌──────────────────────────────────────────────┐
│  1. CORE PROMPT                              │
│     Identidade base da instância             │
│     ("Você é o assistente da Empresa X...")  │
├──────────────────────────────────────────────┤
│  2. TOOL / SKILL INSTRUCTIONS (dinâmico)     │
│     Injetado pelo registry para cada         │
│     skill/tool ativada na instância          │
│     ("Use search_database quando o usuário  │
│      perguntar sobre estoque...")            │
├──────────────────────────────────────────────┤
│  3. CONTEXT / CONSTRAINTS                    │
│     Regras de segurança, formato de saída,   │
│     limites de escopo                        │
└──────────────────────────────────────────────┘
```

Quando o Tenant Admin ativa ou desativa uma skill no dashboard, o backend busca o "Manual de Uso" dessa skill no registry e reconstrói o prompt automaticamente. O LLM só conhece as ferramentas descritas no prompt que recebe.

### Princípios de design

**Agente base único**: Não há código customizado por tenant. O agente base é definido pela plataforma e cobre todos os casos de uso via configuração.

**Instância como unidade de consumo**: Tenants criam instâncias do agente base. Cada instância tem nome, identidade, skills ativas, ferramentas, agentes vinculados e canais próprios.

**Prompt sanduíche**: O sistema de prompts é composto por blocos montados em runtime. Ativar uma skill = injetar seu bloco de instruções. Desativar = remover o bloco.

**Hand-off via tool fantasy**: Agentes vinculados são expostos ao LLM como ferramentas fantasma (`transfer_to_agent_X`). A descrição da tool define quando usá-la; a execução interrompe o fluxo atual e dispara o agente destino com um resumo de hand-off e uma janela controlada de mensagens recentes.

**Configuração dinâmica**: Toda capability é calculada por sessão. Se uma tool está desativada na instância, ela não aparece no prompt nem é executável.

**Isolamento por tenant**: Dados, sessões, documentos e configurações são sempre isolados. Sem cross-tenant access.

**Observabilidade nativa**: Cada execução emite traces, métricas e logs. Não é um addon.

---

## 4. Backend — Arquitetura Detalhada

### Estrutura de diretórios

```
backend/
├── main.py
├── config.py
├── database/
│   ├── connection.py          # AsyncPG pool + TenantContext
│   ├── migrations/            # Alembic
│   └── repositories/
│       ├── instances.py
│       ├── skills.py
│       ├── tools.py
│       ├── links.py
│       ├── sessions.py
│       └── documents.py
├── api/
│   └── v1/
│       ├── superadmin/
│       │   ├── tenants.py
│       │   ├── users.py
│       │   ├── skills.py      # Gestão do catálogo de skills
│       │   └── tools.py       # Gestão do catálogo de tools
│       ├── tenant/
│       │   ├── instances.py   # CRUD de instâncias
│       │   ├── skills.py      # Ativar/desativar skills por instância
│       │   ├── tools.py       # Ativar/desativar tools por instância
│       │   ├── links.py       # Vincular agentes (hand-off)
│       │   ├── documents.py
│       │   ├── channels.py
│       │   └── members.py
│       ├── agent/
│       │   ├── chat.py        # POST /instances/{id}/chat (SSE)
│       │   └── sessions.py
│       └── auth/
│           ├── login.py
│           ├── register.py
│           └── invitations.py
├── engine/
│   ├── prompt_builder.py      # Monta o prompt sanduíche dinamicamente
│   ├── executor.py            # Orquestra execução LangGraph
│   ├── router.py              # Classifier de intenção para hand-off proativo
│   ├── handoff.py             # Lógica de transferência entre instâncias
│   ├── state.py               # AgentState
│   └── nodes/
│       ├── llm_node.py
│       ├── tool_node.py
│       └── rag_node.py
├── rag/
│   ├── indexer.py
│   ├── retriever.py
│   └── embeddings.py
├── skills/
│   ├── registry.py            # Resolve skills ativas por instância
│   └── executor.py            # Executa skills com credenciais do tenant
├── tools/
│   ├── registry.py
│   ├── executor.py
│   └── builtin/
│       ├── web_search.py
│       ├── calculator.py
│       ├── http_request.py
│       └── sql_query.py
├── observability/
│   ├── tracing.py
│   └── metrics.py
├── outbound/
│   ├── mapper.py              # Resolve templates do outbound_sync_config
│   ├── publisher.py           # Publica eventos na fila Redis
│   └── worker.py              # POST/PUT assíncrono para destinos externos
├── workers/
│   ├── document_indexer.py
│   ├── outbound_sync.py
│   └── notification_sender.py
└── dependencies/
    ├── auth.py
    ├── db.py
    └── tenant.py
```

### Endpoint de chat com streaming SSE

```python
# api/v1/agent/chat.py

@router.post("/instances/{instance_id}/chat")
async def chat(
    instance_id: UUID,
    body: ChatRequest,
    request: Request,
    context: AgentContext = Depends(verify_agent_api_key)
):
    executor = AgentExecutor(
        instance_id=instance_id,
        tenant_id=context.tenant_id,
    )

    async def event_stream():
        run = executor.start_stream(
            message=body.message,
            session_id=body.session_id,
        )
        async for event in run:
            if await request.is_disconnected():
                await run.cancel()
                break
            yield f"data: {event.to_json()}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
```

---

## 10. Observabilidade

### Traces por execução

Cada run emite um trace com:
- `tenant_id`, `instance_id`, `session_id`
- Prompt completo montado (core + skill instructions + constraints)
- Tokens de entrada e saída
- Tools e skills chamadas
- Hand-offs realizados (source → target instance)
- Tempo de execução por nó
- Chunks RAG recuperados e scores

### Métricas Prometheus

```
agent_runs_total{tenant_id, instance_id, status}
agent_run_duration_seconds{tenant_id, instance_id}
agent_tokens_used_total{tenant_id, instance_id, type}  # input | output
agent_tool_calls_total{tenant_id, instance_id, tool_slug}
agent_handoffs_total{tenant_id, source_instance, target_instance}
agent_prompt_validation_total{tenant_id, instance_id, level}
agent_prompt_density_score{tenant_id, instance_id}
agent_rag_chunks_retrieved{tenant_id, instance_id}
outbound_sync_jobs_total{tenant_id, instance_id, channel, status}
outbound_sync_deadletter_total{tenant_id, instance_id, channel}
```

### Dashboard de analytics (por tenant)

- Conversas por dia/semana
- Skills e tools mais usadas
- Hand-offs mais frequentes
- Tempo médio de resposta
- Taxa de resolução (sem hand-off vs com hand-off)
- Status de indexação RAG por coleção
- Falhas e dead-letter do Outbound Data Bridge

---

## 11. Frontend — Arquitetura e Jornadas

### Stack

Next.js 14 (App Router) · TypeScript · Tailwind CSS · shadcn/ui · React Query · Zustand

### Estrutura de rotas

```
/login
/register
/awaiting                         ← aguardando aprovação

/dashboard
├── /instances                    ← listagem de instâncias
│   ├── /new                      ← criar nova instância
│   └── /[id]
│       ├── /edit                 ← editar identidade e prompt base
│       ├── /skills               ← ativar/desativar skills
│       ├── /tools                ← ativar/desativar tools
│       ├── /links                ← configurar hand-off para outros agentes
│       ├── /rag                  ← selecionar coleções RAG disponíveis
│       ├── /channels             ← configurar API, widget, webhook, WhatsApp e outbound sync
│       └── /playground           ← testar a instância em tempo real
│
├── /knowledge                    ← gestão de documentos e coleções RAG
├── /analytics                    ← métricas e logs
└── /settings
    ├── /members                  ← gestão de membros e convites
    └── /credentials              ← credenciais de skills (ex: API key do CRM)

/superadmin
├── /tenants
├── /users
├── /skills                       ← catálogo global de skills
└── /tools                        ← catálogo global de tools
```

### Jornada do Tenant Admin: configurar uma instância

```
1. Dashboard → "Nova Instância"
   → Nomear, definir core prompt (identidade), escolher modelo

2. Aba "Skills"
   → Catálogo de skills disponíveis (web_search, CRM lookup, stock check...)
   → Toggle para ativar → prompt_block é injetado automaticamente
   → Se skill requer credencial → link para /settings/credentials

3. Aba "Agentes Vinculados"
   → Selecionar instância destino
   → Definir nome da tool e descrição do trigger
   → Escolher modo: LLM Decision ou Router Classifier

4. Aba "RAG"
   → Selecionar quais coleções de documentos ficam disponíveis
   → Ver status por coleção: Empty, Indexing, Ready, Partial ou Failed
   → Quando houver Indexing/Partial, exibir progresso e aviso de que a skill de RAG ainda não usa 100% da base nova

5. Aba "Canais"
   → Ativar canal API → copiar API key gerada
   → Ativar widget → configurar domínios permitidos e copiar script
   → Advanced Settings → configurar Outbound Data Bridge e mapping de campos

6. Aba "Playground"
   → Testar a instância com o prompt montado em tempo real
   → Ver trace da execução: nós visitados, skills chamadas, chunks RAG
   → Mostrar alerta quando o RAG consultar coleções ainda em Indexing ou Partial
```

### Visualização do prompt montado

O playground exibe o prompt sanduíche atual da instância, mostrando claramente as três camadas:

```
┌─ Core Prompt ──────────────────────────────────────────────┐
│ Você é o assistente da Empresa X, especializado em suporte │
│ ao cliente. Seja claro, empático e objetivo.               │
├─ Skill Instructions (3 skills ativas) ─────────────────────┤
│ [web_search] Você tem acesso à ferramenta 'web_search'.    │
│ Use-a para buscar informações atualizadas sobre produtos.  │
│                                                             │
│ [stock_check] Você tem acesso à ferramenta 'stock_check'.  │
│ Use-a sempre que o usuário perguntar sobre disponibilidade.│
│                                                             │
│ [transfer_to_finance] Você tem acesso à ferramenta         │
│ 'transfer_to_finance_agent'. Use quando o cliente quiser   │
│ falar sobre faturas ou cobranças.                          │
├─ Constraints ───────────────────────────────────────────────┤
│ Responda no idioma do usuário. Não invente dados.          │
└─────────────────────────────────────────────────────────────┘
```

---

## 12. Infraestrutura e Deployment

### Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                        Load Balancer                        │
└───────────────────────────┬─────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
       Next.js          FastAPI         Widget CDN
       (Frontend)       (Backend)       (JS estático)
            │               │
            └───────┬───────┘
                    │
        ┌───────────┼────────────┐
        │           │            │
   PostgreSQL     Redis        Qdrant
   (dados)      (cache/queue)  (vetores)
                    │
          Background Workers
   (indexação/notificações/outbound sync)
```

### Docker Compose (desenvolvimento)

```yaml
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [postgres, redis, qdrant]
    environment:
      DATABASE_URL: postgresql+asyncpg://...
      REDIS_URL: redis://redis:6379
      QDRANT_URL: http://qdrant:6333

  worker:
    build: ./backend
    command: rq worker document_indexing outbound_sync notifications
    depends_on: [postgres, redis, qdrant]

  postgres:
    image: postgres:16
    volumes: [postgres_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine

  qdrant:
    image: qdrant/qdrant:latest
    volumes: [qdrant_data:/qdrant/storage]
```

---

## 13. Segurança

### Isolamento de dados

Todas as queries exigem `tenant_id` explícito. RLS é segunda camada de defesa. Nenhum endpoint retorna dados cross-tenant.

### Proteção de credenciais

API keys de LLM providers encriptadas com AES-256-GCM. Credenciais de skills armazenadas como referências (`secret_ref`) para cofre externo (HashiCorp Vault, AWS Secrets Manager). API keys de canais armazenadas apenas como hash SHA-256 — exibidas em claro somente na criação. Auth Headers e tokens de APIs externas usados pelo Outbound Data Bridge seguem o mesmo padrão de `secret_ref`, criptografia e redaction.

### Proteção da execução

Tools executadas com timeout configurável (default 30s). `sql_query` usa credenciais read-only, limite de linhas e bloqueio de comandos mutáveis. Validação de domínio obrigatória para widgets. Rate limiting por `agent_api_key` via Redis token bucket.

### Auditoria

Audit log imutável (INSERT only) para todas as ações de admin. Retenção: 30 dias starter, 1 ano enterprise.

### Comunicação

HTTPS obrigatório em produção (TLS 1.3). CORS configurado por tenant com origins explícitos. Secrets nunca em logs.

---
