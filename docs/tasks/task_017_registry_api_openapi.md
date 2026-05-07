# Task: TASK-017 - APIs Registry e Documentacao OpenAPI

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-017 |
| **Group** | REGISTRY |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_03_registry.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

As APIs do registry devem ser utilizaveis via Swagger/OpenAPI e seguir contratos de seguranca.

## Objectives

- [x] Documentar summaries e descriptions das rotas.
- [x] Garantir response models Pydantic.
- [x] Garantir security OpenAPI em rotas protegidas.
- [x] Criar e executar validador OpenAPI.

## Non-Goals

- Criar documentacao externa ao Swagger.
- Criar frontend administrativo.

## Stage Boundaries

Esta task cobre o contrato HTTP do Stage 03.

## Dependencies

- TASK-013
- TASK-014
- TASK-016

## Inputs & Contracts

- **Inputs**: rotas FastAPI do registry.
- **Outputs**: OpenAPI valido para Swagger.
- **Schemas**: modelos Pydantic de registry.

## Constraints & Rules

1. Rotas protegidas devem declarar Bearer auth no OpenAPI.
2. Rotas tenant-scoped devem documentar `X-Tenant-ID`.
3. Respostas nao devem vazar segredos.

## Implementation Checklist

- [x] Criar skill `endpoint-contract-guardian`.
- [x] Criar `scripts/validate_openapi.py`.
- [x] Aplicar summaries e descriptions nas rotas novas.
- [x] Executar validacao OpenAPI.

## Acceptance Criteria

- [x] Validador OpenAPI passa.
- [x] Swagger lista rotas com tags e contratos claros.
- [x] Rotas protegidas aparecem com security.
- [x] Headers tenant-scoped aparecem como obrigatorios.

## Verification

```bash
backend\.venv\Scripts\python scripts\validate_openapi.py
```

## Risks & Rollback

- **Risks**: Swagger incompleto dificulta integracao e testes de consumidores.
- **Rollback**: bloquear merge de rotas sem contrato OpenAPI ate corrigir.

## Execution Log

- `[2026-05-07 13:00]`: Skill e script de validacao OpenAPI iniciados.
- `[2026-05-07 13:20]`: Validador OpenAPI passou com rotas de registry documentadas.
