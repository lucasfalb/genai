# Task: TASK-034 - Stage 05 API Bruno e Workflow Verification

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-034 |
| **Group** | SECURITY |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_05_base_multitenant_workflows.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Codex |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-08 |

## Context

O Stage 05 cria endpoints centrais de autenticacao, administracao superadmin, members/RBAC, invitations, instancias, registry, chat SSE, system settings e tenant AI settings. Antes de avancar, a API, OpenAPI, Bruno, testes e tasks precisam estar coerentes.

## Objectives

- [x] Executar suite pytest completa.
- [x] Executar validador OpenAPI.
- [x] Executar validador de tasks.
- [x] Conferir cobertura Bruno para todos os endpoints novos do Stage 05.

## Non-Goals

- [x] Teste de carga.
- [x] Validador automatizado dedicado de Bruno.

## Stage Boundaries

Esta task valida somente workflows base do Stage 05 e regressao dos stages anteriores.

## Dependencies

- TASK-026
- TASK-027
- TASK-028
- TASK-029
- TASK-030
- TASK-031
- TASK-032
- TASK-033
- TASK-035
- TASK-039
- TASK-040
- TASK-062

## Inputs & Contracts

- **Inputs**: backend, migrations, Bruno collection e scripts de validacao.
- **Outputs**: evidencias de validacao completa.
- **Schemas**: OpenAPI e arquivos `.bru`.
- **Bruno coverage**: Auth, Superadmin/Admin, Superadmin/EmailTemplates, Superadmin/SystemSettings, TenantMembers, TenantInvitations, TenantAgentInstances, TenantRegistry, TenantSettings e Agent.

## Constraints & Rules

1. Toda rota nova deve ter summary, description, auth e responses adequados.
2. Toda rota nova deve ter request Bruno correspondente.
3. Todo placeholder Bruno deve existir em `Local.bru`.
4. Tasks `COMPLETED` nao podem ter checklist pendente.

## Implementation Checklist

- [x] Conferir `genai-endpoints/` contra rotas novas.
- [x] Rodar `pytest`.
- [x] Rodar `validate_openapi.py`.
- [x] Rodar `validate_tasks.py`.
- [x] Registrar pendencias residuais no stage.

## Acceptance Criteria

- [x] Pytest passa.
- [x] OpenAPI passa.
- [x] Tasks passam.
- [x] Bruno cobre workflows auth, tenant, members, invitations, instances, registry, chat e settings.

## Verification

```bash
cd backend
.\.venv\Scripts\python -m pytest -q
cd ..
backend\.venv\Scripts\python scripts\validate_openapi.py
python scripts\validate_tasks.py
rg --files genai-endpoints
```

Resultado registrado:

- `pytest -q`: 133 passed, 1 warning.
- `validate_openapi.py`: OK.
- `validate_tasks.py`: OK.
- `genai-endpoints/`: requests presentes para os dominios Stage 05.

## Risks & Rollback

- **Risks**: fluxo manual no Bruno ainda depende de variaveis locais validas (`access_token`, `tenant_id`, `instance_id`, tokens transacionais).
- **Rollback**: reabrir TASK-034 se nova rota Stage 05 for adicionada sem request Bruno ou se validador OpenAPI/tasks falhar.

## Execution Log

- `[2026-05-07 15:40]`: Task criada para validacao final do bloco base multitenant.
- `[2026-05-08 00:00]`: Suite completa, OpenAPI, tasks e cobertura Bruno revisadas; Stage 05 API workflow marcado como validado.
