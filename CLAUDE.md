# CLAUDE.md — GenAI Platform

Leia este arquivo antes de qualquer acao. Evita re-exploracao desnecessaria do codebase.

---

## O Projeto

SaaS multi-tenant de **Agent Registry**: plataforma unica de agentes configuráveis por tenant via dashboard.
Tenants criam **instancias** do agente base, configuram skills/tools/RAG/canais e fazem hand-off entre instancias.

**Stack**: FastAPI + LangGraph + PostgreSQL + Redis + Qdrant + OpenAI-compatible LLMs

---

## Documentacao — Como Consultar

Antes de implementar qualquer coisa, leia o stage relevante:

| Arquivo | Conteudo |
|---------|----------|
| `docs/platform_technical_spec.md` | Especificacao completa (fonte canonica) |
| `docs/architecture_overview.md` | Visao macro, stack, frontend, infraestrutura |
| `docs/map.md` | Roadmap, dependencias entre stages |
| `docs/stages/stage_0X_*.md` | Detalhe tecnico de cada stage |
| `docs/tasks/stage_0X_tasks.md` | Index de tasks por stage |
| `docs/tasks/task_XXX_*.md` | Detalhes de cada task executavel |

**Regra**: sempre ler o stage file e o task file antes de implementar.

---

## Mapa do Backend

```
backend/
├── pyproject.toml              # Deps: fastapi, langgraph, openai, tiktoken, cryptography, redis, sqlalchemy, alembic
├── app/
│   ├── main.py                 # FastAPI app + todos os routers registrados aqui
│   ├── config.py               # Settings (pydantic-settings, le .env ../  )
│   ├── cache.py                # redis_client global
│   ├── rbac.py                 # Permission enum, has_permission()
│   ├── registry_cache.py       # ToolMetadataCache (Redis TTL 600s)
│   ├── responses.py            # api_success(), exception handlers
│   ├── schemas.py              # TODOS os Pydantic request/response models
│   ├── security.py             # JWT: create/decode_access_token
│   └── workflow_audit.py       # record_tenant_mutation()
├── api/v1/
│   ├── agent.py                # POST /agent/instances/{id}/chat (SSE streaming)
│   ├── auth.py                 # /auth/*
│   ├── registry.py             # /registry/* (skills, tools, ativacoes, credenciais)
│   ├── tenant_agent_instances.py  # /tenant/instances/*
│   ├── tenant_ai_config.py        # /tenant/ai-config (GET/PUT/DELETE)
│   ├── tenant_members.py
│   ├── tenant_invitations.py
│   └── superadmin/
│       ├── admin.py            # /superadmin/tenants+users
│       ├── ai_config.py        # /superadmin/ai-config (GET/PUT/DELETE)
│       ├── email_templates.py
│       └── registry.py
├── database/
│   ├── connection.py           # engine (asyncpg), TenantContext, tenant_connection()
│   ├── migrations/versions/    # Alembic — ultimo: 0008_platform_tenant_ai_configs
│   └── repositories/
│       ├── users.py
│       ├── sessions.py         # create_session, get_session, append_message
│       ├── auth_tokens.py
│       ├── registry.py         # load_metadata() para tools/skills
│       ├── agent_instances.py  # AgentInstanceRepository (CRUD completo)
│       ├── ai_configs.py       # AIConfigRepository (platform + tenant)
│       ├── memberships.py
│       ├── invitations.py
│       ├── audit.py
│       └── versions.py
├── dependencies/
│   └── auth.py                 # get_connection, require_permission(Permission.X), require_superadmin
└── engine/
    ├── state.py                # AgentState TypedDict
    ├── base_graph.py           # LangGraph: rag→llm(async/OpenAI)→dispatch/handoff
    ├── bootstrap.py            # RunBootstrap.prepare(): instance+prompt+history+ai_config
    ├── executor.py             # AgentExecutor.start_stream() → AgentRunStream
    ├── session_lock.py         # Redis SETNX TTL 45s
    ├── prompt_builder.py       # PromptBuilder.build(): core+skills+tools+constraints
    ├── prompt_sanitizer.py     # MAX_SYSTEM_TOKENS=6000, tiktoken
    ├── prompt_cache.py         # Redis TTL 600s
    └── ai_provider.py          # AIProviderResolver + Fernet encrypt/decrypt
```

---

## Padroes Obrigatorios

### Envelope de resposta
```python
# Sempre usar helpers — nunca dict() raw
return api_success(data, message="...")          # {"status":"success","data":...}
raise HTTPException(status_code, "mensagem")    # capturado pelo handler global
```

### Autenticacao e permissao
```python
# Superadmin
_: None = Depends(require_superadmin)

# Tenant (resolve TenantContext com role RBAC)
context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES))
connection: AsyncConnection = Depends(get_connection)
```

### Isolamento de tenant
- Toda query inclui `tenant_id` explicitamente
- Antes de queries com RLS: `SELECT set_config('app.current_tenant_id', :tid, true)`
- Nunca retornar dados cross-tenant

### Cache Redis (invalidar em mutacoes)
```python
await ToolMetadataCache(connection).invalidate(tenant_id=..., instance_id=...)
await PromptCache(connection).invalidate(tenant_id=..., instance_id=...)
```
Chaves: `tenant:{id}:instance:{id}:tool_metadata` e `tenant:{id}:instance:{id}:system_prompt`

### AI Provider (nunca hardcode)
```python
# Hierarquia: tenant_ai_configs → platform_ai_configs → OPENAI_API_KEY (.env, dev only)
resolved = await AIProviderResolver(connection).resolve(tenant_id=tenant_id)
# api_key nunca em logs; api_key_hint: "****" em responses
```

### LLM Node (tests)
```python
# Sempre monkeypatch llm_node em testes — nunca chamar OpenAI real
import engine.base_graph as bg
async def fake_llm(state): return {"final_response": "Fake."}
monkeypatch.setattr(bg, "llm_node", fake_llm)
```

---

## Skills Ativas (/.claude/skills/)

### /genai-task-guardian
Use ao criar/atualizar tasks e stages. Regras:
- Ler `docs/stages/stage_XX.md` antes de criar tasks
- Um arquivo por task: `docs/tasks/task_XXX_slug.md`
- Sections obrigatorias: Context, Objectives, Non-Goals, Stage Boundaries, Dependencies, Inputs & Contracts, Constraints & Rules, Implementation Checklist, Acceptance Criteria, Verification, Risks & Rollback, Execution Log
- Execution Log format: `- \`[YYYY-MM-DD HH:MM]\`: evento`
- Validar: `python scripts/validate_tasks.py`

### /commit-guardian
Use ao criar commits. Regras:
- Conventional Commits: `type(scope): summary`
- Types: feat, fix, docs, test, refactor, chore, build, ci, perf, security
- Scopes: auth, tenants, members, registry, engine, rag, handoff, channels, audit, tasks, bruno, docs, db, api
- Body com bullets + `Refs: TASK-XXX`

### /endpoint-contract-guardian
Use ao criar/mudar endpoints. Regras:
- Todo route: tags, summary, description, response_model, status codes documentados
- Superadmin: `require_superadmin`; Tenant: `require_permission(...)`
- Nunca expor secrets, hashes, credentials
- Criar/atualizar Bruno request em `genai-endpoints/`
- Validar: `backend\.venv\Scripts\python scripts\validate_openapi.py`

### /pr-workflow
Use ao iniciar tasks, criar branches, abrir PRs ou promover releases. Regras:
- Model: `task/TASK-XXX-slug` → `dev` → `prod`
- Nunca commitar direto em `dev` ou `prod`
- PRs sempre targeting `dev`; promoção para `prod` via merge `--no-ff`
- Um branch por task, deletar após merge

---

## Comandos de Desenvolvimento

```powershell
# Testes (rodar de dentro de backend/)
$env:OPENAI_API_KEY="sk-..."
.venv\Scripts\python -m pytest -x -q

# Migrations
.venv\Scripts\alembic upgrade head

# Validacoes
python scripts\validate_tasks.py
backend\.venv\Scripts\python scripts\validate_openapi.py

# Servicos (rodar da raiz)
docker compose up -d postgres redis qdrant
```

---

## Estado de Implementacao (2026-05-07)

| Stage | Tasks | Status | Testes |
|-------|-------|--------|--------|
| 01 Core DB | — | DONE | — |
| 02 Auth/RBAC | — | DONE | — |
| 03 Registry | — | DONE | — |
| 04 Engine (base) | — | DONE | — |
| 05 Multi-tenant workflows | TASK-032,033 | DONE | 92 passando |
| 05 Prompt Runtime | TASK-036 a 040 | DONE | — |
| 05 AI Provider Config | TASK-061 | DONE | — |
| 06 RAG | TASK-041 a 047 | PENDING | — |
| 07 Handoff | TASK-048 a 053 | PENDING | — |
| 08 Channels | TASK-054 a 060 | PENDING | — |

**Proximo**: TASK-041 — migrations + repos para collections/documents (Stage 06 RAG)

---

## Variaveis de Ambiente Necessarias

| Variavel | Onde | Uso |
|----------|------|-----|
| `DATABASE_URL` | .env | PostgreSQL asyncpg |
| `REDIS_URL` | .env | Redis |
| `JWT_SECRET_KEY` | .env | JWT signing |
| `AI_CONFIG_ENCRYPTION_KEY` | env/secrets | Fernet master key (nao o API key do LLM) |
| `OPENAI_API_KEY` | .env (dev only) | Fallback se nao houver platform_ai_config |

**Producao**: `OPENAI_API_KEY` nao deve existir. Configurar via `/superadmin/ai-config`.

---

## Convencoes de Arquivos

- Novos repositorios: `backend/database/repositories/nome.py`
- Novos endpoints tenant: `backend/api/v1/tenant_nome.py`, prefix `/tenant/nome`
- Novos endpoints superadmin: `backend/api/v1/superadmin/nome.py`, prefix `/superadmin/nome`
- Registrar router em `backend/app/main.py`
- Schemas em `backend/app/schemas.py` (nao criar arquivos separados)
- Testes: `backend/tests/test_stage_XX_nome.py`
