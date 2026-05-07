# Task: TASK-034 - Stage 05 API Bruno e Workflow Verification

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-034 |
| **Group** | SECURITY |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_05_base_multitenant_workflows.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O Stage 05 cria muitos endpoints centrais. Antes de avançar, a API, OpenAPI, Bruno, testes e tasks precisam estar coerentes.

## Objectives

- [ ] Executar suite pytest completa.
- [ ] Executar validador OpenAPI.
- [ ] Executar validador de tasks.
- [ ] Conferir cobertura Bruno para todos os endpoints novos.

## Non-Goals

- Teste de carga.
- Validador automatizado dedicado de Bruno.

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

## Inputs & Contracts

- **Inputs**: backend, migrations, Bruno collection e scripts de validacao.
- **Outputs**: evidencias de validacao completa.
- **Schemas**: OpenAPI e arquivos `.bru`.

## Constraints & Rules

1. Toda rota nova deve ter summary, description, auth e responses adequados.
2. Toda rota nova deve ter request Bruno correspondente.
3. Todo placeholder Bruno deve existir em `Local.bru`.
4. Tasks `COMPLETED` nao podem ter checklist pendente.

## Implementation Checklist

- [ ] Conferir `genai-endpoints/` contra rotas novas.
- [ ] Rodar `pytest`.
- [ ] Rodar `validate_openapi.py`.
- [ ] Rodar `validate_tasks.py`.
- [ ] Registrar pendencias residuais no stage.

## Acceptance Criteria

- [ ] Pytest passa.
- [ ] OpenAPI passa.
- [ ] Tasks passam.
- [ ] Bruno cobre workflows auth, tenant, members, invitations e instances.

## Verification

```bash
docker compose up -d postgres redis qdrant
cd backend
alembic upgrade head
pytest
cd ..
backend\.venv\Scripts\python scripts\validate_openapi.py
python scripts\validate_tasks.py
```

## Risks & Rollback

- **Risks**: avancar com workflows base incompletos causa regressao nos stages de IA e canais.
- **Rollback**: manter Stage 05 aberto e bloquear stages dependentes.

## Execution Log

- `[2026-05-07 15:40]`: Task criada para validacao final do bloco base multitenant.
