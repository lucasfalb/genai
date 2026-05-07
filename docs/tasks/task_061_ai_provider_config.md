# Task: TASK-061 - AI Provider Config por Tenant e Plataforma

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-061 |
| **Group** | ENGINE |
| **Status** | DONE |
| **Stage Ref** | `docs/stages/stage_05_prompts.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Cada tenant deve poder configurar seu proprio provedor de AI (API key, modelo, base_url). A plataforma define um config global como fallback. API keys sao criptografadas em repouso com Fernet; nunca aparecem em logs ou respostas de listagem.

## Objectives

- [x] Criar `platform_ai_configs` e `tenant_ai_configs` via migration `0008`.
- [x] Implementar `AIProviderResolver` em `engine/ai_provider.py` com hierarquia tenant → platform → fallback dev.
- [x] Implementar `encrypt_api_key` / `decrypt_api_key` com Fernet.
- [x] Criar `database/repositories/ai_configs.py` com upsert/get/delete para ambas as tabelas.
- [x] Criar `api/v1/superadmin/ai_config.py` (GET/PUT/DELETE para config de plataforma).
- [x] Criar `api/v1/tenant_ai_config.py` (GET/PUT/DELETE para config por tenant).
- [x] Wire `AIProviderResolver` no `RunBootstrap.prepare()`.
- [x] Usar `ai_api_key` e `ai_base_url` do `AgentState` no `llm_node`.
- [x] Remover dependencia de `OPENAI_API_KEY` do `.env` para producao.

## Non-Goals

- UI de configuracao de provider (frontend futuro).
- Suporte a provedores alem de OpenAI na API de chat (compativel com `base_url`).

## Stage Boundaries

Extensao do Stage 05 Prompt Runtime. Sem impacto em stages anteriores.

## Dependencies

- TASK-039 (LLM node)

## Inputs & Contracts

- **Inputs**: `provider`, `api_key` (plaintext, criptografado antes de persistir), `default_model`, `base_url`.
- **Outputs**: `ResolvedAIConfig(provider, api_key, base_url, default_model)` no estado do agente.
- **Schemas**: `PlatformAIConfigRequest/Response`, `TenantAIConfigRequest/Response`.

## Constraints & Rules

1. API key nunca aparece em respostas de listagem — apenas `api_key_hint: "****"`.
2. Criptografia via Fernet com `AI_CONFIG_ENCRYPTION_KEY` (env de infraestrutura, nao o API key em si).
3. Hierarquia de resolucao: tenant_ai_config → platform_ai_config → `OPENAI_API_KEY` (somente dev).
4. Em producao, `OPENAI_API_KEY` nao deve existir; a ausencia de config lanca `AIProviderNotConfigured`.
5. `base_url` permite uso de providers compativeis com OpenAI (Azure, etc.).

## Implementation Checklist

- [x] Migration `20260507_0008_platform_tenant_ai_configs.py`.
- [x] `engine/ai_provider.py`: `ResolvedAIConfig`, `encrypt_api_key`, `decrypt_api_key`, `AIProviderResolver`.
- [x] `database/repositories/ai_configs.py`: `AIConfigRepository`.
- [x] `api/v1/superadmin/ai_config.py`: endpoints superadmin.
- [x] `api/v1/tenant_ai_config.py`: endpoints tenant.
- [x] `app/schemas.py`: `PlatformAIConfigRequest/Response`, `TenantAIConfigRequest/Response`.
- [x] `engine/state.py`: campos `ai_api_key`, `ai_base_url`.
- [x] `engine/bootstrap.py`: chama `AIProviderResolver.resolve()`.
- [x] `engine/base_graph.py`: usa `state["ai_api_key"]` e `state["ai_base_url"]`.
- [x] `app/main.py`: registra novos routers.
- [x] `tests/test_stage_05_ai_provider.py`: encrypt/decrypt round-trip, resolver fallback, platform, tenant override.

## Acceptance Criteria

- [x] `encrypt_api_key` / `decrypt_api_key` round-trip correto.
- [x] Resolver usa tenant config quando disponivel.
- [x] Resolver cai para platform config quando tenant nao tem config.
- [x] Resolver cai para `OPENAI_API_KEY` como fallback de dev.
- [x] Resolver lanca `AIProviderNotConfigured` quando nada esta configurado.
- [x] API key nunca aparece em respostas.
- [x] 92 testes passam.

## Verification

```bash
cd backend
alembic upgrade head
pytest tests/test_stage_05_ai_provider.py
pytest tests/test_stage_05_prompt_runtime.py
pytest
```

## Risks & Rollback

- **Risks**: Rotacao de `AI_CONFIG_ENCRYPTION_KEY` requer re-criptografia de todos os registros existentes.
- **Rollback**: Manter `OPENAI_API_KEY` no `.env` como fallback ate todos os tenants terem config propria.

## Execution Log

- `[2026-05-07 00:00]`: Task criada e implementada — 92 testes passando.
