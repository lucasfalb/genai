# Task: TASK-062 - System Settings e Tenant AI Config Consolidation

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-062 |
| **Group** | ENGINE |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_05_prompts.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O modelo atual criou tres fontes concorrentes para configuracao de AI: `llm_providers`, `platform_ai_configs` e `tenant_ai_configs`. Isso aumenta a complexidade sem necessidade: provider global pertence a configuracao operacional da plataforma, enquanto override por tenant pertence ao proprio registro do tenant.

Tambem faltam configuracoes globais gerenciaveis por superadmin, como nome da plataforma, URL publica, SMTP, modo manutencao e registro publico ativo. Essas configuracoes nao devem ficar espalhadas no `.env` nem em tabelas especificas por feature.

O modelo precisa ser extensivel: configuracoes criticas devem ter colunas tipadas para seguranca, validacao e query direta, mas o superadmin tambem deve poder criar keys avulsas para uso no frontend sem exigir nova migration a cada ajuste de produto.

## Objectives

- [x] Remover as tabelas `llm_providers`, `platform_ai_configs` e `tenant_ai_configs`.
- [x] Adicionar colunas de AI provider diretamente em `tenants`.
- [x] Criar tabela singleton `system_settings` para configuracoes globais da plataforma, com colunas tipadas e keys customizadas em JSONB.
- [x] Migrar dados existentes de `tenant_ai_configs` para `tenants`.
- [x] Migrar o provider ativo de `platform_ai_configs` para `system_settings`.
- [x] Atualizar `AIProviderResolver` para resolver tenant override em `tenants` e fallback global em `system_settings`.
- [x] Substituir endpoints antigos de AI config por endpoints de system settings e tenant settings.
- [x] Expor contrato publico seguro para frontend consumir settings permitidos.
- [x] Atualizar schemas, testes, OpenAPI e Bruno conforme novo contrato.

## Non-Goals

- Implementar UI de administracao.
- Rotacionar chaves criptograficas existentes.
- Suportar multiplos providers globais ativos ao mesmo tempo.
- Manter compatibilidade de tabela com `llm_providers`, `platform_ai_configs` ou `tenant_ai_configs`.

## Stage Boundaries

Esta task refatora a camada de configuracao operacional do Stage 05 Prompt Runtime. Ela altera schema, repositorios, endpoints administrativos e resolucao de provider, mas nao altera o LLM node nem o contrato de chat.

## Dependencies

- TASK-029
- TASK-032
- TASK-039
- TASK-061

## Inputs & Contracts

- **Inputs**: configuracao global da plataforma, configuracao AI por tenant e dados legados das tabelas antigas.
- **Outputs**: `ResolvedAIConfig` usando `tenants` e `system_settings`, endpoints administrativos sem vazamento de segredos e endpoint publico de settings seguros para frontend.
- **Schemas**:
  - `tenants.ai_provider`, `tenants.ai_default_model`, `tenants.ai_api_key_encrypted`, `tenants.ai_enabled`, `tenants.ai_configured_at`, `tenants.ai_configured_by`.
  - `system_settings.platform_name`, `system_settings.platform_public_url`, `system_settings.platform_logo_url`, `system_settings.maintenance_mode`, `system_settings.registration_enabled`, `system_settings.smtp_host`, `system_settings.smtp_port`, `system_settings.smtp_secure`, `system_settings.smtp_user`, `system_settings.smtp_pass_encrypted`, `system_settings.smtp_from`, `system_settings.ai_provider`, `system_settings.ai_default_model`, `system_settings.ai_api_key_encrypted`, `system_settings.custom_settings`, `system_settings.public_settings`, `system_settings.updated_by`.
  - `custom_settings`: JSONB para keys operacionais avulsas, nao expostas publicamente por padrao.
  - `public_settings`: JSONB allowlist/materializacao das keys que podem ser consumidas pelo frontend publico.

## Constraints & Rules

1. `system_settings` deve ser singleton: uma linha operacional, com constraint que impede multiplas linhas.
2. Segredos (`ai_api_key`, `smtp_pass`) nunca podem aparecer em response, logs, audit metadata ou resource versions.
3. Segredos persistidos devem usar criptografia existente via `AI_CONFIG_ENCRYPTION_KEY` ou helper renomeado para segredo operacional generico.
4. `AIProviderResolver` deve seguir hierarquia: tenant em `tenants` quando `ai_enabled=true` e key presente; caso contrario, fallback global em `system_settings`; por fim fallback dev em `OPENAI_API_KEY` apenas em ambiente local.
5. `llm_providers` deve ser removida da fonte canonica e dos testes de schema; catalogo de provider nao deve ser tabela enquanto o produto usa um provider configuravel simples via `provider/model`.
6. Endpoints antigos `/superadmin/ai-config` e `/tenant/ai-config` devem ser removidos ou substituidos por rotas novas com o contrato consolidado.
7. Mudancas globais por superadmin devem registrar audit log global com redacao de segredos.
8. Mudancas tenant-scoped feitas por tenant admin ou superadmin devem registrar audit/version do tenant com actor context.
9. SMTP em `.env` deve ser apenas bootstrap/local fallback; runtime gerenciavel deve vir de `system_settings`.
10. Migrations devem preservar dados existentes antes de dropar tabelas antigas.
11. Configuracoes criticas e segredos nao devem ir para `custom_settings`; devem ter coluna tipada ou estrutura dedicada para validacao e redacao.
12. `custom_settings` deve aceitar apenas valores JSON serializaveis e keys em formato `^[a-z0-9_.-]+$`.
13. Keys em `custom_settings` nao podem usar nomes reservados (`smtp_pass`, `ai_api_key`, `password`, `secret`, `token`, `authorization`, `api_key`) nem variantes case-insensitive.
14. `public_settings` deve ser uma allowlist explicita para frontend; nenhum valor de `custom_settings` deve ser publico automaticamente.
15. Endpoint publico de settings deve retornar somente dados nao sensiveis, por exemplo `platform_name`, `platform_public_url`, `platform_logo_url`, `registration_enabled`, `maintenance_mode` e `public_settings`.

## Implementation Checklist

- [x] Criar migration que adiciona colunas AI em `tenants`.
- [x] Criar migration que cria `system_settings` singleton com colunas operacionais globais, `custom_settings JSONB` e `public_settings JSONB`.
- [x] Migrar dados ativos de `tenant_ai_configs` para colunas em `tenants`.
- [x] Migrar dados ativos de `platform_ai_configs` para `system_settings`.
- [x] Dropar `tenant_ai_configs`, `platform_ai_configs` e `llm_providers`.
- [x] Remover referencias a `llm_providers` de docs, tests e schema canonical.
- [x] Renomear/ajustar repositorio `AIConfigRepository` para operar em `tenants` e `system_settings`.
- [x] Atualizar `AIProviderResolver`.
- [x] Criar/ajustar endpoints superadmin de `system_settings`.
- [x] Criar endpoints superadmin para setar/remover keys em `custom_settings` e promover keys seguras para `public_settings`.
- [x] Criar endpoint publico read-only de settings seguros para bootstrap do frontend.
- [x] Criar/ajustar endpoints tenant-scoped para AI settings do tenant.
- [x] Atualizar Bruno e `validate_openapi.py`, quando necessario.
- [x] Atualizar testes de migration/schema, resolver, endpoints e redacao de segredos.

## Acceptance Criteria

- [x] Banco nao possui `llm_providers`, `platform_ai_configs` ou `tenant_ai_configs` apos migration head.
- [x] `tenants` possui colunas de AI provider por tenant.
- [x] `system_settings` guarda plataforma, SMTP, flags operacionais, provider global e settings customizados.
- [x] Superadmin consegue criar, atualizar e remover keys customizadas sem migration.
- [x] Frontend consegue consumir apenas settings explicitamente publicos.
- [x] Keys customizadas sensiveis ou reservadas sao rejeitadas.
- [x] Resolver usa tenant override antes do fallback global.
- [x] Responses nunca retornam `ai_api_key`, `ai_api_key_encrypted`, `smtp_pass` ou `smtp_pass_encrypted`.
- [x] Superadmin consegue gerir system settings com audit global.
- [x] Tenant admin consegue gerir AI settings do tenant com audit/version tenant-scoped.
- [x] Tests e docs deixam de tratar `llm_providers` como tabela canonica.

## Verification

```bash
cd backend
alembic upgrade head
pytest tests/test_stage_01_schema.py
pytest tests/test_stage_05_ai_provider.py
pytest
cd ..
backend\.venv\Scripts\python scripts\validate_openapi.py
python scripts\validate_tasks.py
```

## Risks & Rollback

- **Risks**: migration incorreta pode perder API keys criptografadas ou quebrar tenants sem config propria.
- **Rollback**: restaurar backup antes da migration; em ambiente dev, manter fallback `OPENAI_API_KEY` ate validar `system_settings`.

## Execution Log

- `[2026-05-07 21:00]`: Task criada para consolidar configuracao AI em `tenants`, substituir provider global por `system_settings` e remover tabelas redundantes.
- `[2026-05-07 21:10]`: Task ajustada para suportar extensibilidade: colunas tipadas para settings criticos e `custom_settings/public_settings` JSONB para keys avulsas controladas pelo superadmin e consumiveis com seguranca pelo frontend.
- `[2026-05-07 21:45]`: Implementada migration `20260507_0009`, repositorio consolidado, novos endpoints `system-settings`/`tenant/settings/ai`, Bruno, OpenAPI e testes focados.
- `[2026-05-07 21:50]`: Confirmado versionamento: mudancas tenant AI usam `record_tenant_mutation` com audit e `resource_versions`; mudancas globais de `system_settings` usam audit global com snapshots redigidos.
- `[2026-05-07 22:00]`: Validado `alembic upgrade head`, `validate_openapi.py`, `validate_tasks.py`, `pytest -q` com 129 testes passando e introspeccao do banco confirmando apenas `system_settings` entre as tabelas de configuracao.
- `[2026-05-07 22:10]`: `ai_base_url` removido do contrato inicial de AI provider; `platform_logo_url` adicionado a `system_settings` e ao endpoint publico para branding do frontend.
