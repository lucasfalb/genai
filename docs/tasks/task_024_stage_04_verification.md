# Task: TASK-024 - Validacao Stage 04

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-024 |
| **Group** | ENGINE |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_04_engine.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O Stage 04 deve fechar com testes de executor, lock, SSE, OpenAPI e task docs.

## Objectives

- [x] Executar suite pytest completa.
- [x] Executar validador OpenAPI.
- [x] Executar validador de tasks.
- [x] Confirmar status/checklists sincronizados.

## Non-Goals

- Testes de carga de streaming.
- Validacao de LLM real.

## Stage Boundaries

Esta task valida somente entregas do Stage 04 e regressao dos stages anteriores.

## Dependencies

- TASK-022
- TASK-023

## Inputs & Contracts

- **Inputs**: ambiente local com Postgres, Redis e Qdrant.
- **Outputs**: evidencias de validacao.
- **Schemas**: nenhum schema novo.

## Constraints & Rules

1. Validacao deve passar antes de abrir Stage 05.
2. `COMPLETED` nao pode ter checklist pendente.
3. Rotas novas devem passar no validador OpenAPI.

## Implementation Checklist

- [x] Subir dependencias via Docker Compose.
- [x] Rodar migrations.
- [x] Rodar testes.
- [x] Rodar validadores.

## Acceptance Criteria

- [x] Pytest passa.
- [x] OpenAPI passa.
- [x] Tasks passam.
- [x] Pendencias do Stage 04 ficam documentadas.

## Verification

```bash
pytest
backend\.venv\Scripts\python scripts\validate_openapi.py
python scripts\validate_tasks.py
```

## Risks & Rollback

- **Risks**: abrir Stage 05 com executor instavel.
- **Rollback**: manter Stage 04 em progresso e bloquear novas tasks dependentes.

## Execution Log

- `[2026-05-07 14:20]`: Task criada a partir do Stage 04.
- `[2026-05-07 15:20]`: Docker services confirmados ativos; pytest completo, OpenAPI validator e task validator passaram.
