# Stage 01 — Core DB, Multi-Tenancy e RLS

_Fonte canônica: [`../platform_technical_spec.md`](../platform_technical_spec.md). Este stage reorganiza o conteúdo técnico sem substituir a especificação completa._

## Objetivo

Definir a base relacional da plataforma: tenants, usuários, isolamento por `tenant_id`, RLS, sessões, mensagens, auditoria e o schema tenant-scoped completo. Este stage mantém o schema SQL completo como fonte de verdade para evitar divergência entre domínios.

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
│   ├── llm_providers
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
