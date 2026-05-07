# Agent Registry Platform — Especificação Técnica

> Stack: LangGraph · FastAPI · Next.js · PostgreSQL · Qdrant · Redis · OpenTelemetry

---

## Índice

1. [Visão Geral e Princípios](#1-visão-geral-e-princípios)
2. [Modelo de Dados e Multi-Tenancy](#2-modelo-de-dados-e-multi-tenancy)
3. [Sistema de Autenticação e RBAC](#3-sistema-de-autenticação-e-rbac)
4. [Backend — Arquitetura Detalhada](#4-backend--arquitetura-detalhada)
5. [Motor de Execução — Prompt Dinâmico e Skill Injection](#5-motor-de-execução--prompt-dinâmico-e-skill-injection)
6. [Orquestração de Agentes e Hand-off](#6-orquestração-de-agentes-e-hand-off)
7. [RAG e Knowledge Base](#7-rag-e-knowledge-base)
8. [Agent Wrapper — API e Widget](#8-agent-wrapper--api-e-widget)
9. [Outbound Data Bridge (External Sync)](#9-outbound-data-bridge-external-sync)
10. [Observabilidade](#10-observabilidade)
11. [Frontend — Arquitetura e Jornadas](#11-frontend--arquitetura-e-jornadas)
12. [Infraestrutura e Deployment](#12-infraestrutura-e-deployment)
13. [Segurança](#13-segurança)
14. [Roadmap de Implementação](#14-roadmap-de-implementação)

---

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

## 2. Modelo de Dados e Multi-Tenancy

### Estratégia de isolamento

Schema PostgreSQL único (`public`) com `tenant_id` explícito e Row-Level Security (RLS) em todas as tabelas tenant-scoped. O backend injeta `tenant_id` via `TenantContext` em cada query.

### Schema principal

```
PostgreSQL (schema: public)
│
├── [GLOBAIS]
│   ├── tenants
│   ├── users
│   ├── memberships
│   ├── invitations
│   ├── system_settings
│   ├── skill_definitions        ← catálogo global de skills
│   ├── tool_definitions         ← catálogo global de tools
│   └── audit_logs
│
└── [TENANT-SCOPED]
    ├── agent_instances          ← instâncias do agente base por tenant
    ├── agent_instance_skills    ← skills ativas por instância
    ├── agent_instance_tools     ← tools ativas por instância
    ├── agent_links              ← vínculos de hand-off entre instâncias
    ├── tool_credentials         ← credenciais de tools por tenant
    ├── collections              ← coleções de documentos RAG
    ├── documents
    ├── document_permissions
    ├── sessions
    ├── messages
    └── agent_channel_configs    ← canais de consumo por instância
```

### Entidades globais

```sql
-- Tenants
CREATE TABLE tenants (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug        TEXT UNIQUE NOT NULL,
  name        TEXT NOT NULL,
  plan        TEXT NOT NULL DEFAULT 'starter',  -- starter | pro | enterprise
  status      TEXT NOT NULL DEFAULT 'active',   -- active | suspended | trial
  settings    JSONB NOT NULL DEFAULT '{}',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Users (globais — podem estar em múltiplos tenants)
CREATE TABLE users (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email           TEXT UNIQUE NOT NULL,
  name            TEXT,
  avatar_url      TEXT,
  password_hash   TEXT,
  is_superadmin   BOOLEAN NOT NULL DEFAULT false,
  status          TEXT NOT NULL DEFAULT 'pending',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Memberships
CREATE TABLE memberships (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id),
  tenant_id   UUID NOT NULL REFERENCES tenants(id),
  role        TEXT NOT NULL,  -- tenant_admin | member | viewer
  status      TEXT NOT NULL DEFAULT 'pending',
  invited_by  UUID REFERENCES users(id),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, tenant_id)
);

-- Catálogo de skills disponíveis na plataforma
CREATE TABLE skill_definitions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            TEXT NOT NULL,
  slug            TEXT UNIQUE NOT NULL,
  description     TEXT,
  category        TEXT,              -- crm | database | communication | finance | ...
  prompt_block    TEXT NOT NULL,     -- bloco de instruções injetado no prompt sanduíche
  tool_schema     JSONB NOT NULL,    -- schema JSON da tool para o LLM
  executor        TEXT NOT NULL,     -- handler Python da skill
  input_schema    JSONB NOT NULL,
  output_schema   JSONB NOT NULL,
  requires_credential BOOLEAN NOT NULL DEFAULT false,
  credential_schema   JSONB,         -- campos necessários para credencial
  is_active       BOOLEAN NOT NULL DEFAULT true,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Catálogo de tools utilitárias (web_search, calculator, http_request...)
CREATE TABLE tool_definitions (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  slug        TEXT UNIQUE NOT NULL,
  description TEXT,
  category    TEXT,
  prompt_block TEXT NOT NULL,        -- instrução injetada no prompt sanduíche
  schema      JSONB NOT NULL,
  executor    TEXT NOT NULL,
  is_builtin  BOOLEAN NOT NULL DEFAULT false,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Entidades tenant-scoped

```sql
-- Instâncias do agente base (uma por caso de uso/canal)
CREATE TABLE agent_instances (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  name            TEXT NOT NULL,                     -- "Assistente de Suporte", "Agente Financeiro"
  description     TEXT,
  core_prompt     TEXT NOT NULL,                     -- identidade base da instância
  model           TEXT NOT NULL DEFAULT 'gpt-4.1-mini',
  temperature     FLOAT NOT NULL DEFAULT 0.2,
  status          TEXT NOT NULL DEFAULT 'inactive',  -- inactive | active | paused
  rag_scope       JSONB NOT NULL DEFAULT '[]',        -- collection_ids habilitadas
  created_by      UUID NOT NULL REFERENCES users(id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Skills ativas por instância (com configuração específica)
CREATE TABLE agent_instance_skills (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  instance_id     UUID NOT NULL REFERENCES agent_instances(id),
  skill_id        UUID NOT NULL REFERENCES skill_definitions(id),
  is_enabled      BOOLEAN NOT NULL DEFAULT true,
  config          JSONB NOT NULL DEFAULT '{}',        -- config específica desta skill na instância
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(instance_id, skill_id)
);

-- Tools ativas por instância
CREATE TABLE agent_instance_tools (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  instance_id     UUID NOT NULL REFERENCES agent_instances(id),
  tool_id         UUID NOT NULL REFERENCES tool_definitions(id),
  is_enabled      BOOLEAN NOT NULL DEFAULT true,
  config          JSONB NOT NULL DEFAULT '{}',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(instance_id, tool_id)
);

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

-- Credenciais de tools por tenant
CREATE TABLE tool_credentials (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  skill_id        UUID NOT NULL REFERENCES skill_definitions(id),
  credential_data JSONB NOT NULL DEFAULT '{}',  -- referências a secrets, nunca valores em claro
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(tenant_id, skill_id)
);

-- Coleções de documentos para RAG
CREATE TABLE collections (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  name            TEXT NOT NULL,
  description     TEXT,
  indexing_status TEXT NOT NULL DEFAULT 'empty',  -- empty | indexing | ready | partial | failed
  indexing_progress FLOAT NOT NULL DEFAULT 0,     -- 0.0 a 1.0
  document_count  INTEGER NOT NULL DEFAULT 0,
  indexed_count   INTEGER NOT NULL DEFAULT 0,
  failed_count    INTEGER NOT NULL DEFAULT 0,
  last_indexed_at TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Documentos enviados para RAG
CREATE TABLE documents (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  collection_id   UUID NOT NULL REFERENCES collections(id),
  filename        TEXT NOT NULL,
  source_type     TEXT NOT NULL,       -- upload | url | api
  status          TEXT NOT NULL DEFAULT 'uploaded',  -- uploaded | indexing | indexed | failed
  chunk_count     INTEGER NOT NULL DEFAULT 0,
  error_message   TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  indexed_at      TIMESTAMPTZ
);

-- Canais de consumo por instância
CREATE TABLE agent_channel_configs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  instance_id     UUID NOT NULL REFERENCES agent_instances(id),
  channel         TEXT NOT NULL,        -- api | widget | webhook | whatsapp
  config          JSONB NOT NULL DEFAULT '{}',
  outbound_sync_config JSONB NOT NULL DEFAULT '{}',
  is_active       BOOLEAN NOT NULL DEFAULT false,
  api_key         TEXT,                 -- hash; exibida apenas na criação
  allowed_origins TEXT[],               -- para widget: domínios permitidos
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(tenant_id, instance_id, channel)
);

-- Sessões de conversa
CREATE TABLE sessions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  instance_id     UUID NOT NULL REFERENCES agent_instances(id),
  channel         TEXT NOT NULL,
  user_ref        TEXT,
  metadata        JSONB NOT NULL DEFAULT '{}',
  started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_message_at TIMESTAMPTZ
);

-- Mensagens
CREATE TABLE messages (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  session_id      UUID NOT NULL REFERENCES sessions(id),
  sequence_no     BIGINT NOT NULL,
  role            TEXT NOT NULL,       -- user | assistant | tool
  content         TEXT NOT NULL,
  metadata        JSONB NOT NULL DEFAULT '{}',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(session_id, sequence_no)
);

-- Audit log (imutável)
CREATE TABLE audit_logs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   UUID REFERENCES tenants(id),
  user_id     UUID REFERENCES users(id),
  action      TEXT NOT NULL,
  resource    TEXT NOT NULL,
  resource_id TEXT,
  metadata    JSONB NOT NULL DEFAULT '{}',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índices
CREATE INDEX idx_agent_instances_tenant ON agent_instances(tenant_id);
CREATE INDEX idx_agent_instance_skills_instance ON agent_instance_skills(instance_id, is_enabled);
CREATE INDEX idx_agent_instance_tools_instance ON agent_instance_tools(instance_id, is_enabled);
CREATE INDEX idx_agent_links_source ON agent_links(source_instance_id, is_enabled);
CREATE INDEX idx_collections_tenant_status ON collections(tenant_id, indexing_status);
CREATE INDEX idx_documents_collection_status ON documents(collection_id, status);
CREATE INDEX idx_sessions_tenant_instance ON sessions(tenant_id, instance_id, started_at DESC);
CREATE INDEX idx_messages_session ON messages(session_id, created_at);
```

### Vector Store (Qdrant)

Coleções compartilhadas por plan/modelo, filtradas por payload `tenant_id` e `collection_id`. Coleções dedicadas apenas em Enterprise.

```json
{
  "tenant_id": "abc123",
  "collection_id": "uuid-da-colecao",
  "document_id": "uuid-do-documento",
  "chunk_index": 3,
  "embedding_model": "text-embedding-3-large",
  "text": "conteúdo do chunk..."
}
```

---

## 3. Sistema de Autenticação e RBAC

### Fluxo de autenticação

JWT com refresh tokens. O access token representa a identidade global; o contexto de tenant é selecionado por header `X-Tenant-ID`.

```
POST /auth/register
  → Cria user status="pending"
  → Envia email de verificação
  → Aguarda convite ou atribuição de role

POST /auth/login
  → Valida credenciais
  → Se sem memberships → retorna flag "awaiting_assignment"
  → Se tem membership ativa → emite JWT + refresh token
```

### Roles e permissões

| Permissão | Superadmin | Tenant Admin | Member | Viewer |
|-----------|:---:|:---:|:---:|:---:|
| Gerir tenants e users globais | ✓ | — | — | — |
| Criar/editar instâncias de agente | — | ✓ | — | — |
| Ativar/desativar skills e tools | — | ✓ | — | — |
| Vincular agentes (configurar hand-off) | — | ✓ | — | — |
| Configurar canais | — | ✓ | ✓ | — |
| Upload de documentos RAG | — | ✓ | ✓ | — |
| Convidar membros | — | ✓ | — | — |
| Ver logs e traces | — | ✓ | ✓ | ✓ |
| Interagir com agentes | — | ✓ | ✓ | ✓ |

### Middleware de autorização

```python
# dependencies/auth.py

async def get_tenant_context(request: Request, user = Depends(get_current_user)) -> TenantContext:
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id:
        raise HTTPException(400, "X-Tenant-ID header obrigatório")

    cache_key = f"membership:{user.sub}:{tenant_id}"
    cached = await redis.get(cache_key)
    if cached:
        return TenantContext.model_validate_json(cached)

    membership = await db.get_active_membership(user.sub, tenant_id)
    if not membership:
        raise HTTPException(403, "Sem acesso a este tenant")

    ctx = TenantContext(tenant_id=tenant_id, user_id=user.sub, role=membership.role)
    await redis.setex(cache_key, 300, ctx.model_dump_json())
    return ctx
```

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

## 5. Motor de Execução — Prompt Dinâmico e Skill Injection

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

### AgentState

```python
# engine/state.py

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    handoff_summary: Optional[str]

    # Contexto da sessão
    session_id: str
    tenant_id: str
    instance_id: str
    channel: str

    # Prompt montado para esta execução
    system_prompt: str

    # Capabilities calculadas no bootstrap
    available_tools: List[str]        # tools ativas na instância
    available_skills: List[str]       # skills ativas na instância
    tool_schemas: List[dict]          # schemas enviados ao LLM
    linked_agents: List[dict]         # agentes vinculados como tools fantasma

    # RAG
    rag_scope: List[str]              # collection_ids habilitadas
    retrieved_chunks: List[dict]

    # Execução
    pending_tool_calls: Optional[List[dict]]
    tool_results: Optional[List[dict]]
    handoff_target: Optional[str]     # instance_id para hand-off

    # Output
    final_response: Optional[str]
    citations: Optional[List[dict]]
```

### Bootstrap de run

```python
# engine/executor.py

class RunBootstrap:
    async def prepare(self, instance_id: str, tenant_id: str, session_id: str) -> AgentState:
        prompt = await PromptBuilder(self.db, self.redis).build(instance_id, tenant_id)

        metadata = await ToolMetadataCache(self.db, self.redis).get(
            tenant_id=tenant_id,
            instance_id=instance_id,
        )
        active_skills = metadata.active_skills
        active_tools = metadata.active_tools
        linked_agents = metadata.linked_agents

        # Monta schemas de tools para o LLM
        tool_schemas = (
            [s.definition.tool_schema for s in active_skills] +
            [t.definition.schema for t in active_tools] +
            [self._build_handoff_schema(link) for link in linked_agents]
        )

        instance = await self.db.get_instance(instance_id, tenant_id)

        return AgentState(
            session_id=session_id,
            tenant_id=tenant_id,
            instance_id=instance_id,
            system_prompt=prompt.full,
            available_tools=[t.definition.slug for t in active_tools],
            available_skills=[s.definition.slug for s in active_skills],
            tool_schemas=tool_schemas,
            linked_agents=[self._link_to_dict(l) for l in linked_agents],
            rag_scope=instance.rag_scope,
            messages=[],
            handoff_summary=None,
            retrieved_chunks=[],
        )

    def _build_handoff_schema(self, link) -> dict:
        return {
            "name": link.transfer_tool_name,
            "description": link.trigger_description,
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Motivo da transferência"}
                },
                "required": ["reason"]
            }
        }
```

### Cache de metadata e credenciais

```python
# skills/registry.py

class ToolMetadataCache:
    async def get(self, tenant_id: str, instance_id: str) -> ToolMetadata:
        key = f"tenant:{tenant_id}:instance:{instance_id}:tool_metadata"
        cached = await self.redis.get(key)
        if cached:
            return ToolMetadata.model_validate_json(cached)

        metadata = await self.db.load_tool_metadata(instance_id, tenant_id)
        await self.redis.set(key, metadata.model_dump_json(), ex=600)
        return metadata

    async def invalidate(self, tenant_id: str, instance_id: str) -> None:
        await self.redis.delete(f"tenant:{tenant_id}:instance:{instance_id}:tool_metadata")


class CredentialCache:
    async def get_decrypted(self, tenant_id: str, credential_id: str) -> dict:
        key = f"tenant:{tenant_id}:credential:{credential_id}:decrypted"
        cached = await self.redis.get(key)
        if cached:
            return decrypt_local_cache_payload(cached)

        encrypted = await self.db.get_credential_ref(tenant_id, credential_id)
        secret = await self.vault.decrypt(encrypted.secret_ref)

        # TTL curto: reduz latência sem manter segredo vivo por muito tempo.
        await self.redis.set(key, encrypt_local_cache_payload(secret), ex=60)
        return secret
```

### Grafo LangGraph do agente base

```python
# engine/base_graph.py

from langgraph.graph import StateGraph, END
from engine.state import AgentState

def create_base_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("rag", rag_node)
    graph.add_node("llm", llm_node)
    graph.add_node("dispatch", dispatch_node)
    graph.add_node("handoff", handoff_node)

    graph.set_entry_point("rag")
    graph.add_edge("rag", "llm")

    graph.add_conditional_edges(
        "llm",
        route_after_llm,
        {
            "tool_call": "dispatch",
            "handoff": "handoff",
            "respond": END,
        }
    )

    graph.add_edge("dispatch", "llm")
    graph.add_edge("handoff", END)

    return graph.compile()

def route_after_llm(state: AgentState) -> str:
    calls = state.get("pending_tool_calls", [])
    if not calls:
        return "respond"
    # Verifica se é um hand-off
    for call in calls:
        if call["name"] in [l["transfer_tool_name"] for l in state["linked_agents"]]:
            return "handoff"
    return "tool_call"
```

---

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

## 7. RAG e Knowledge Base

### Pipeline de indexação

```
Upload de documento (PDF/DOCX/URL)
   ↓
documents.status = uploaded
collections.indexing_status = indexing
   ↓
Worker de indexação (background)
   ↓
Extração de texto → Chunking → Embedding
   ↓
Qdrant (payload: tenant_id, collection_id, document_id, chunk_index)
   ↓
documents.status = indexed | failed
collections.indexing_status = ready | partial | failed
```

### Status de indexação

O `rag_scope` define quais coleções a instância pode consultar, mas a disponibilidade real depende do `indexing_status` da coleção. Enquanto uma coleção está em `indexing`, a skill de RAG pode operar parcialmente com documentos já indexados, mas o frontend deve deixar claro que a base nova ainda não está 100% disponível.

Estados:

- `empty`: coleção criada, sem documentos indexáveis.
- `indexing`: há documentos em processamento.
- `ready`: todos os documentos válidos foram indexados.
- `partial`: parte dos documentos falhou, mas existe conteúdo pesquisável.
- `failed`: nenhum documento novo ficou pesquisável.

O backend expõe `indexing_progress`, `document_count`, `indexed_count`, `failed_count` e `last_indexed_at` para a tela de Knowledge Base e para a aba RAG da instância. Uploads grandes devem ser processados por worker em background, com atualização incremental de progresso.

### Retriever com RBAC

```python
# rag/retriever.py

class TenantRetriever:
    async def retrieve(
        self,
        query: str,
        tenant_id: str,
        rag_scope: list[str],  # collection_ids habilitadas na instância
        top_k: int = 5,
    ) -> list[dict]:
        if not rag_scope:
            return []

        ready_scope = await self.db.get_searchable_collections(
            tenant_id=tenant_id,
            collection_ids=rag_scope,
            allowed_statuses=["ready", "partial", "indexing"],
        )
        if not ready_scope:
            return []

        embedding = await self.embedder.embed(query)

        results = await self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            query_filter={
                "must": [
                    {"key": "tenant_id", "match": {"value": tenant_id}},
                    {"key": "collection_id", "match": {"any": ready_scope}},
                    {"key": "document_status", "match": {"value": "indexed"}},
                ]
            },
            limit=top_k,
        )

        return [
            {
                "text": r.payload["text"],
                "source": r.payload.get("source"),
                "score": r.score,
            }
            for r in results
        ]
```

---

## 8. Agent Wrapper — API e Widget

### Canais disponíveis

Cada instância pode ser consumida via API, Widget, Webhook ou WhatsApp. O Tenant Admin ativa e configura cada canal no dashboard e recebe a API key ou credencial específica.

Cada canal também pode receber `outbound_sync_config` em Advanced Settings. Essa configuração define se dados extraídos da conversa serão enviados para uma API ou base externa após a resposta da IA, sem bloquear o streaming para o usuário.

**Canal API:**
```
POST /api/v1/chat
Headers:
  X-Agent-Key: ak_live_...
Body: { "message": "...", "session_id": "..." }
Response: SSE stream de eventos
```

### SessionManager e ResponseManager

O `SessionManager` normaliza entradas vindas de API, Widget, Webhook e WhatsApp para o mesmo contrato interno: `tenant_id`, `instance_id`, `session_id`, `channel`, `sender_id`, `metadata` e mensagem do usuário. Isso mantém o LangGraph independente do canal de origem.

O `ResponseManager` centraliza a etapa final do run: persiste a resposta, envia eventos SSE quando aplicável, registra métricas e aciona integrações assíncronas como o Outbound Data Bridge.

### Concorrência por sessão

Cada `session_id` deve ter no máximo uma execução ativa por vez. Antes de carregar ou gravar estado no checkpointer do LangGraph, o backend adquire um lock distribuído no Redis:

- Chave: `session:{tenant_id}:{session_id}:lock`.
- Aquisição atômica: `SET key run_id NX EX 45`.
- Renovação durante streaming longo.
- Liberação segura apenas se o valor ainda for o mesmo `run_id`.
- Se o lock já existir, a API retorna `409 Conflict` ou enfileira a mensagem em `session:{tenant_id}:{session_id}:queue`, conforme configuração do canal.

O checkpointer mantém `thread_id = session_id`, mas as escritas são serializadas pelo lock. Além disso, cada mensagem persistida recebe `sequence_no` incremental por sessão, garantindo ordenação estável mesmo quando duas requisições chegam quase ao mesmo tempo.

```python
# engine/session_lock.py

class SessionLock:
    async def acquire(self, tenant_id: str, session_id: str, run_id: str) -> bool:
        key = f"session:{tenant_id}:{session_id}:lock"
        return bool(await self.redis.set(key, run_id, nx=True, ex=45))

    async def release(self, tenant_id: str, session_id: str, run_id: str) -> None:
        key = f"session:{tenant_id}:{session_id}:lock"
        await self.redis.eval(
            """
            if redis.call("GET", KEYS[1]) == ARGV[1] then
                return redis.call("DEL", KEYS[1])
            end
            return 0
            """,
            1,
            key,
            run_id,
        )
```

**Canal Widget:**

Script embeddável em qualquer site. Valida o domínio de origem contra `allowed_origins`.
```html


```

**Canal Webhook:**

Recebe mensagens de sistemas externos (WhatsApp, Slack, etc.) e processa assincronamente.
```
POST /api/v1/webhook
Headers: X-Agent-Key: ak_live_...
Body: { "from": "...", "message": "...", "platform": "whatsapp" }
```

**Canal WhatsApp:**

Canal configurável para provedores como Meta Cloud API ou gateways terceiros. Internamente usa o mesmo `SessionManager` e pode compartilhar a infraestrutura de webhook.
```
POST /api/v1/whatsapp/webhook
Headers: X-Provider-Signature: ...
Body: { "from": "+351...", "message": "...", "profile": { "name": "..." } }
```

### Geração automática de API key

Ao ativar um canal, a plataforma gera e exibe a key uma única vez. Internamente é armazenado apenas o hash.

```python
# api/v1/tenant/channels.py

@router.post("/instances/{instance_id}/channels/{channel}/activate")
async def activate_channel(instance_id: UUID, channel: str, tenant: TenantContext = ...):
    raw_key = f"ak_live_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    await db.upsert_channel_config(
        tenant_id=tenant.tenant_id,
        instance_id=instance_id,
        channel=channel,
        outbound_sync_config={
            "enabled": False,
            "destination": {
                "method": "POST",
                "url": None,
                "timeout_seconds": 10,
            },
            "auth_headers_secret_ref": None,
            "field_mapping": {},
            "retry": {"max_attempts": 5, "backoff": "exponential"},
        },
        api_key=key_hash,
        is_active=True,
    )

    # Retorna a key em claro apenas neste momento
    return {"api_key": raw_key, "warning": "Guarde esta key. Ela não será exibida novamente."}
```

### Advanced Settings — outbound_sync_config

```json
{
  "enabled": true,
  "destination": {
    "method": "POST",
    "url": "https://api.cliente.com/leads",
    "timeout_seconds": 10
  },
  "auth_headers_secret_ref": "vault://tenant/acme/outbound/crm_headers",
  "field_mapping": {
    "external_id": "{{ session_id }}",
    "channel": "{{ channel }}",
    "sender": "{{ sender_id }}",
    "name": "{{ metadata.name }}",
    "email": "{{ extracted_entities.email }}",
    "summary": "{{ conversation_summary }}",
    "last_message": "{{ last_user_message }}"
  },
  "retry": {
    "max_attempts": 5,
    "backoff": "exponential"
  }
}
```

O mapping dinâmico permite transformar campos internos em chaves do JSON final. O mapper só publica os campos configurados em `field_mapping`, evitando envio acidental do transcript completo, tool outputs ou dados internos do `AgentState`.

---

## 9. Outbound Data Bridge (External Sync)

### Objetivo

O Outbound Data Bridge permite que canais como API, WhatsApp e Webhooks enviem automaticamente dados extraídos da conversa para uma base de dados ou API externa escolhida pelo tenant. O caso típico é sincronizar leads, tickets, pedidos, entidades extraídas ou resumos de atendimento para um CRM, data warehouse ou backend próprio do cliente.

Essa ponte é assíncrona: a resposta da IA ao usuário não espera o endpoint externo responder.

### Arquitetura lean

```
LangGraph finaliza resposta / entidades
   ↓
ResponseManager persiste resposta e monta payload mapeado
   ↓
OutboundPublisher publica evento mínimo no Redis
   ↓
Worker RQ/Celery consome em background
   ↓
HTTP POST/PUT para API externa do tenant
   ↓
Sucesso, retry com exponential backoff ou dead-letter
```

Componentes:

- **Broker**: Redis existente da stack, reutilizado para fila leve além de lock distribuído e cache.
- **Fila**: RQ ou Celery para Python. RQ é suficiente para a primeira versão; Celery pode ser adotado se houver necessidade de roteamento, prioridades e inspeção operacional mais avançada.
- **Worker**: processo separado do FastAPI, responsável por chamadas externas, retries e dead-letter.
- **Publisher**: roda no caminho quente apenas para mapear dados e enfileirar evento pequeno.

### Integração com SessionManager e ResponseManager

O `SessionManager` continua responsável por resolver `tenant_id`, `session_id`, `channel`, `sender_id` e metadata normalizada de entrada. O `ResponseManager` é o ponto de integração do outbound sync: após persistir a resposta final ou receber `extracted_entities` do grafo LangGraph, ele consulta a configuração do canal e publica o evento assíncrono.

```python
# engine/response_manager.py

class ResponseManager:
    async def finalize(self, state: AgentState, response: AgentResponse) -> None:
        await self.messages.persist_assistant_response(state, response)

        channel_config = await self.channels.get_config(
            tenant_id=state["tenant_id"],
            instance_id=state["instance_id"],
            channel=state["channel"],
        )

        config = channel_config.outbound_sync_config
        if not config.get("enabled"):
            return

        payload = OutboundMapper().render(
            mapping=config["field_mapping"],
            source={
                "tenant_id": state["tenant_id"],
                "instance_id": state["instance_id"],
                "session_id": state["session_id"],
                "channel": state["channel"],
                "sender_id": state.get("sender_id"),
                "metadata": state.get("metadata", {}),
                "extracted_entities": response.extracted_entities,
                "conversation_summary": response.conversation_summary,
                "last_user_message": response.last_user_message,
            },
        )

        await OutboundPublisher(self.redis).enqueue(
            tenant_id=state["tenant_id"],
            channel_config_id=str(channel_config.id),
            method=config["destination"]["method"],
            url=config["destination"]["url"],
            auth_headers_secret_ref=config.get("auth_headers_secret_ref"),
            payload=payload,
            retry=config.get("retry", {}),
        )
```

### Fluxo de execução

1. O LangGraph gera a resposta final e, quando aplicável, `extracted_entities`.
2. O `ResponseManager` persiste a resposta normalmente.
3. O mapper aplica `field_mapping` usando templates como `{{ metadata.name }}` ou `{{ extracted_entities.email }}`.
4. O publisher envia para o Redis apenas o payload mapeado, destino e referência segura de credenciais.
5. O worker consome a fila e executa `POST` ou `PUT`.
6. Em falha temporária, o job é reagendado com exponential backoff.
7. Após esgotar retries, o job vai para dead-letter e aparece no dashboard do canal.

```python
# outbound/worker.py

async def process_outbound_sync(job: OutboundSyncJob) -> None:
    headers = await CredentialCache().get_decrypted_headers(
        tenant_id=job.tenant_id,
        secret_ref=job.auth_headers_secret_ref,
    )

    response = await http_client.request(
        method=job.method,
        url=job.url,
        json=job.payload,
        headers=headers,
        timeout=job.timeout_seconds,
    )
    response.raise_for_status()
```

### Resiliência e Segurança

O Outbound Data Bridge nunca envia o `AgentState` inteiro. O evento da fila contém apenas os campos resultantes do mapping configurado. Isso reduz vazamento acidental de prompts, tool outputs, credenciais ou histórico completo.

Regras obrigatórias:

- Auth Headers e tokens de APIs externas são armazenados como `secret_ref` e tratados com o mesmo nível de criptografia das API keys da instância.
- Secrets nunca entram em logs, traces, payloads da fila ou respostas de API.
- Retentativas usam exponential backoff com jitter para evitar tempestade de chamadas no endpoint do cliente.
- Timeouts curtos por request, default 10s.
- Dead-letter queue para falhas permanentes, com replay manual no dashboard.
- Allowlist opcional de domínios por tenant em planos enterprise.
- Redaction de campos sensíveis nos logs do worker.

### Observabilidade do bridge

```
outbound_sync_jobs_total{tenant_id, instance_id, channel, status}
outbound_sync_duration_seconds{tenant_id, instance_id, channel}
outbound_sync_retries_total{tenant_id, instance_id, channel}
outbound_sync_deadletter_total{tenant_id, instance_id, channel}
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

## 14. Roadmap de Implementação

### Fase 1 — Fundação (semanas 1-3)

- [ ] Monorepo, Docker Compose, CI/CD básico
- [ ] Schema PostgreSQL + migrations (Alembic)
- [ ] Auth: registro, login, JWT, verificação de email
- [ ] RBAC middleware
- [ ] Multi-tenancy: `tenant_id` obrigatório + RLS
- [ ] CRUD de tenants e users (superadmin)
- [ ] Frontend: login, registro, página awaiting, routing por role

### Fase 2 — Agente Base e Prompt Dinâmico (semanas 4-6)

- [ ] Catálogo de skills e tools (superadmin)
- [ ] CRUD de instâncias por tenant
- [ ] Ativação de skills e tools por instância
- [ ] Cache Redis de prompt composto, metadata de tools/skills e credenciais decriptadas com TTL curto
- [ ] Invalidação do cache de prompt/metadata em saves administrativos no dashboard
- [ ] `PromptBuilder`: montagem do prompt sanduíche em runtime
- [ ] `PromptSanitizer`: limite de tokens, densidade de instruções, conflitos entre blocos e nomes únicos de tools
- [ ] Validação de output por canal/schema antes de persistir resposta final
- [ ] `AgentState` e `RunBootstrap`
- [ ] Grafo LangGraph base (rag → llm → dispatch)
- [ ] Lock distribuído por `session_id` para serializar escritas do checkpointer
- [ ] Streaming SSE end-to-end
- [ ] Playground básico no frontend

### Fase 3 — Hand-off entre Agentes (semanas 7-8)

- [ ] Tabela `agent_links` e API de configuração
- [ ] Tools fantasma geradas dinamicamente por instância
- [ ] `handoff_node`: interrupção e transferência com Resumo de Hand-off sanitizado
- [ ] `IntentRouter`: classifier para modo proativo
- [ ] UI de configuração de vínculos no dashboard
- [ ] Testes de hand-off end-to-end

### Fase 4 — RAG e Knowledge Base (semanas 9-11)

- [ ] Pipeline de indexação de documentos (PDF, DOCX, URL)
- [ ] Status de indexação por documento e coleção (`empty`, `indexing`, `ready`, `partial`, `failed`)
- [ ] UI de progresso/alerta de Indexing na Knowledge Base, aba RAG e Playground
- [ ] Integração Qdrant com filtros por tenant e collection
- [ ] `TenantRetriever` com RBAC
- [ ] UI de gestão de coleções e documentos
- [ ] Configuração de RAG scope por instância

### Fase 5 — Canais e Widget (semanas 12-13)

- [ ] Geração de API keys por canal
- [ ] Widget JavaScript embeddável
- [ ] Validação de domínio para widget
- [ ] Webhook receiver
- [ ] Canal WhatsApp via webhook/provider adapter
- [ ] UI de configuração de canais
- [ ] `outbound_sync_config` em Advanced Settings dos canais
- [ ] Outbound Data Bridge com Redis broker, worker RQ/Celery e retries com exponential backoff
- [ ] Mapping dinâmico com templates e dead-letter/replay no dashboard

### Fase 6 — Observabilidade e Analytics (semanas 14-16)

- [ ] Traces por execução (skills, tools, hand-offs, RAG)
- [ ] Métricas Prometheus + Grafana
- [ ] Dashboard de analytics por tenant
- [ ] Logs estruturados com redaction de dados sensíveis

### Fase 7 — Polish e Enterprise (semanas 17-20)

- [ ] SSO (SAML, OAuth)
- [ ] Billing e limites de plano
- [ ] Rate limiting avançado
- [ ] Exportação de analytics
- [ ] Disaster recovery e backups automáticos
- [ ] Integrações de knowledge (Notion, Confluence, S3)
