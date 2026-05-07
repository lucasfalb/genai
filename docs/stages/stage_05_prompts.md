# Stage 05 — Prompt Runtime, Sandwich e Sanitization

_Fonte canônica: [`../platform_technical_spec.md`](../platform_technical_spec.md). Este stage reorganiza o conteúdo técnico sem substituir a especificação completa._

## Objetivo

Documentar a montagem dinâmica do prompt, cache do prompt composto, injection de skills/tools/hand-offs, validação de densidade e contratos de output.

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

### PromptBuilder — montagem em runtime

O `PromptBuilder` é responsável por montar o prompt sanduíche a cada execução. Ele consulta o banco para obter skills e tools ativas da instância e injeta os blocos de instrução correspondentes.

Para evitar cold start em skills e tools, o registry usa Redis como cache de curta duração para metadata calculada por instância (`tool_metadata`, schemas, prompt blocks e configuração efetiva). O `PromptBuilder` também cacheia o `SystemPrompt` composto e já sanitizado por instância, evitando múltiplas queries e recomposição textual antes de cada chamada ao LLM. Credenciais decriptadas também podem ser cacheadas por TTL curto, sempre com chave escopada por `tenant_id` e `credential_id`, nunca emitidas em logs ou traces.

TTL recomendado:

- Prompt composto: 5 a 15 minutos.
- Metadata de tools/skills: 5 a 15 minutos.
- Credenciais decriptadas: 30 a 120 segundos.
- Invalidação imediata em alterações salvas pelo Admin no dashboard: `core_prompt`, skill, tool, credencial, vínculo de hand-off, modelo, constraints ou configuração de canal.

```python
# engine/prompt_builder.py

class PromptBuilder:
    def __init__(self, db: TenantDB, redis: Redis):
        self.db = db
        self.redis = redis

    async def build(self, instance_id: str, tenant_id: str) -> SystemPrompt:
        cached_prompt = await PromptCache(self.redis).get(
            tenant_id=tenant_id,
            instance_id=instance_id,
        )
        if cached_prompt:
            return cached_prompt

        instance = await self.db.get_instance(instance_id, tenant_id)

        metadata = await ToolMetadataCache(self.db, self.redis).get(
            tenant_id=tenant_id,
            instance_id=instance_id,
        )

        active_skills = metadata.active_skills
        active_tools = metadata.active_tools
        linked_agents = metadata.linked_agents

        # Camada 1: Core prompt (identidade da instância)
        core = instance.core_prompt

        # Camada 2: Tool/Skill instructions (injetadas dinamicamente)
        instructions = []

        for skill in active_skills:
            instructions.append(skill.definition.prompt_block)

        for tool in active_tools:
            instructions.append(tool.definition.prompt_block)

        # Agentes vinculados são expostos como tools fantasma
        for link in linked_agents:
            instructions.append(
                f"Você tem acesso à ferramenta '{link.transfer_tool_name}'. "
                f"{link.trigger_description}"
            )

        tool_section = "\n\n".join(instructions) if instructions else ""

        # Camada 3: Constraints
        constraints = self._build_constraints(instance)

        prompt = SystemPrompt(
            core=core,
            tool_instructions=tool_section,
            constraints=constraints,
            full=f"{core}\n\n{tool_section}\n\n{constraints}".strip(),
        )

        validated_prompt = await PromptSanitizer().validate(prompt, metadata)
        await PromptCache(self.redis).set(
            tenant_id=tenant_id,
            instance_id=instance_id,
            prompt=validated_prompt,
        )
        return validated_prompt

    def _build_constraints(self, instance) -> str:
        return (
            "Responda sempre no idioma do usuário. "
            "Não invente dados ou números. "
            "Se não souber, diga que não sabe."
        )
```

### Cache do Prompt Composto

O cache do prompt composto fica acima do cache de metadata: em cache hit, o bootstrap evita recompor blocos, recalcular densidade e consultar tabelas de skills/tools/links. A chave deve incluir `tenant_id` e `instance_id`; se houver variações relevantes por canal ou modelo, esses campos entram na chave.

```python
# engine/prompt_cache.py

class PromptCache:
    TTL_SECONDS = 600

    def __init__(self, redis: Redis):
        self.redis = redis

    def key(self, tenant_id: str, instance_id: str) -> str:
        return f"tenant:{tenant_id}:instance:{instance_id}:system_prompt"

    async def get(self, tenant_id: str, instance_id: str) -> Optional[SystemPrompt]:
        cached = await self.redis.get(self.key(tenant_id, instance_id))
        if not cached:
            return None
        return SystemPrompt.model_validate_json(cached)

    async def set(self, tenant_id: str, instance_id: str, prompt: SystemPrompt) -> None:
        await self.redis.set(
            self.key(tenant_id, instance_id),
            prompt.model_dump_json(),
            ex=self.TTL_SECONDS,
        )

    async def invalidate(self, tenant_id: str, instance_id: str) -> None:
        await self.redis.delete(self.key(tenant_id, instance_id))
```

Toda rota administrativa que salva configuração de instância chama `PromptCache.invalidate(...)` e `ToolMetadataCache.invalidate(...)` na mesma transação lógica da alteração. Isso mantém baixa latência no caminho quente e consistência forte o suficiente para mudanças feitas no dashboard.

### Prompt Sanitization e validação de output

Como o prompt final é composto dinamicamente, a plataforma precisa validar a combinação de `core_prompt`, skills, tools, hand-offs e constraints antes de chamar o LLM. Essa etapa evita que uma instância com muitas capabilities gere um prompt grande demais, contraditório ou com contratos de resposta incompatíveis.

Validações obrigatórias:

- Limite máximo de tokens para o `system_prompt` final, com margem para histórico, RAG e resposta.
- Cálculo de `instruction_density`, medindo quantas instruções, tools, skills e hand-offs competem dentro do mesmo prompt.
- Detecção de conflitos simples entre blocos, como dois formatos obrigatórios de resposta ou instruções opostas de idioma/tom.
- Deduplicação de instruções repetidas quando várias skills compartilham a mesma regra operacional.
- Validação de nomes únicos para tools e hand-offs, impedindo colisão de schemas.
- Seleção de um `output_contract` por execução: texto livre, JSON estruturado ou schema específico do canal.

Se a validação falhar, a execução não deve seguir silenciosamente. O backend retorna erro configurável para o dashboard/playground ou degrada de forma controlada, desativando blocos opcionais de menor prioridade. Quando o prompt ainda é válido, mas a densidade está alta, a execução pode prosseguir com alerta visível no dashboard e evento de observabilidade.

Níveis recomendados:

- `ok`: prompt abaixo de 60% do budget e baixa densidade.
- `warning`: prompt entre 60% e 80% do budget ou muitas instruções concorrentes.
- `critical`: prompt acima de 80% do budget, alta densidade ou conflitos potenciais.
- `blocked`: prompt acima do limite absoluto ou conflito explícito de contrato.

```python
# engine/prompt_sanitizer.py

class PromptSanitizer:
    MAX_SYSTEM_TOKENS = 6_000
    WARNING_RATIO = 0.60
    CRITICAL_RATIO = 0.80

    async def validate(self, prompt: SystemPrompt, metadata: ToolMetadata) -> SystemPrompt:
        token_count = count_tokens(prompt.full)
        density = InstructionDensityScorer().score(prompt, metadata)

        if token_count > self.MAX_SYSTEM_TOKENS:
            raise PromptValidationError(
                f"System prompt com {token_count} tokens excede o limite seguro"
            )

        budget_ratio = token_count / self.MAX_SYSTEM_TOKENS
        if budget_ratio >= self.CRITICAL_RATIO or density.level == "critical":
            await self.alerts.emit(
                level="critical",
                code="prompt_density_high",
                token_count=token_count,
                max_tokens=self.MAX_SYSTEM_TOKENS,
                density=density.model_dump(),
            )
        elif budget_ratio >= self.WARNING_RATIO or density.level == "warning":
            await self.alerts.emit(
                level="warning",
                code="prompt_density_warning",
                token_count=token_count,
                max_tokens=self.MAX_SYSTEM_TOKENS,
                density=density.model_dump(),
            )

        tool_names = [
            item.schema["name"]
            for item in metadata.active_tools + metadata.active_skills
        ]
        tool_names += [link.transfer_tool_name for link in metadata.linked_agents]
        if len(tool_names) != len(set(tool_names)):
            raise PromptValidationError("Nomes de tools/hand-offs duplicados")

        conflicts = PromptConflictDetector().scan(prompt.full)
        if conflicts:
            raise PromptValidationError(f"Instruções conflitantes: {conflicts}")

        return prompt


class InstructionDensityScorer:
    def score(self, prompt: SystemPrompt, metadata: ToolMetadata) -> PromptDensity:
        capability_count = (
            len(metadata.active_skills) +
            len(metadata.active_tools) +
            len(metadata.linked_agents)
        )
        imperative_count = count_instruction_markers(prompt.full)
        token_count = count_tokens(prompt.full)

        score = (
            capability_count * 2 +
            imperative_count +
            token_count / 1_000
        )

        level = "ok"
        if score >= 35:
            level = "critical"
        elif score >= 22:
            level = "warning"

        return PromptDensity(
            score=score,
            level=level,
            capability_count=capability_count,
            imperative_count=imperative_count,
            token_count=token_count,
        )
```

O nó final do grafo também valida a saída antes de persistir e transmitir ao usuário. Para canais que exigem JSON ou payload estruturado, a resposta passa por schema validation; se falhar, o agente recebe uma tentativa de reparo com o erro de validação e, após o limite de retries, retorna fallback controlado.

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
