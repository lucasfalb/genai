# Stage 03 — Registry, Skills, Tools e Vault

_Fonte canônica: [`../platform_technical_spec.md`](../platform_technical_spec.md). Este stage reorganiza o conteúdo técnico sem substituir a especificação completa._

## Objetivo

Concentrar o catálogo global de skills/tools, ativações por instância, credenciais tenant-scoped e cache de metadata. O prompt runtime consome este stage para descobrir capacidades disponíveis.

## Tabelas Relevantes

```sql
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

-- Credenciais de tools por tenant
CREATE TABLE tool_credentials (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  skill_id        UUID NOT NULL REFERENCES skill_definitions(id),
  credential_data JSONB NOT NULL DEFAULT '{}',  -- referências a secrets, nunca valores em claro
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(tenant_id, skill_id)
);
```

## Diretórios Relacionados

```text
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

## Segurança de Credenciais

### Proteção de credenciais

API keys de LLM providers encriptadas com AES-256-GCM. Credenciais de skills armazenadas como referências (`secret_ref`) para cofre externo (HashiCorp Vault, AWS Secrets Manager). API keys de canais armazenadas apenas como hash SHA-256 — exibidas em claro somente na criação. Auth Headers e tokens de APIs externas usados pelo Outbound Data Bridge seguem o mesmo padrão de `secret_ref`, criptografia e redaction.

### Proteção da execução

Tools executadas com timeout configurável (default 30s). `sql_query` usa credenciais read-only, limite de linhas e bloqueio de comandos mutáveis. Validação de domínio obrigatória para widgets. Rate limiting por `agent_api_key` via Redis token bucket.

## Implementacao Stage 03

- Catalogo global implementado em endpoints superadmin de `/api/v1/superadmin/registry/skills` e `/api/v1/superadmin/registry/tools`.
- Ativacoes tenant-scoped implementadas em `/api/v1/registry/instances/{instance_id}/skills/{skill_slug}` e `/api/v1/registry/instances/{instance_id}/tools/{tool_slug}` com `X-Tenant-ID`, RLS e permissao `MANAGE_SKILLS_TOOLS`.
- Metadata ativa por instancia e resolvida por `/api/v1/registry/instances/{instance_id}/metadata` e cacheada no Redis por 600 segundos.
- Credenciais tenant-scoped aceitam apenas `secret_ref` e metadata nao sensivel em `/api/v1/registry/credentials/{skill_slug}`. Segredos em claro como `api_key`, `token`, `password` ou `secret` sao rejeitados.
- Contratos de API devem passar em `scripts/validate_openapi.py`; tasks/stages devem passar em `scripts/validate_tasks.py`.
