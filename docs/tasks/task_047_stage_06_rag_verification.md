# Task: TASK-047 - Verificacao Stage 06 RAG

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-047 |
| **Group** | RAG |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_06_rag.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Antes de avancar para handoff, o pipeline RAG completo precisa estar validado: migrations, CRUD de collections, upload de documents, worker de indexacao, retriever e integracao no grafo.

## Objectives

- [ ] Executar suite pytest completa.
- [ ] Executar validador OpenAPI.
- [ ] Executar validador de tasks.
- [ ] Verificar cobertura Bruno para endpoints de collections e documents.
- [ ] Confirmar isolamento cross-tenant no Qdrant.

## Non-Goals

- Teste de carga de indexacao.
- Validacao de qualidade de retrieval.

## Stage Boundaries

Validacao somente do Stage 06 e regressao dos stages anteriores.

## Dependencies

- TASK-041, TASK-042, TASK-043, TASK-044, TASK-045, TASK-046

## Inputs & Contracts

- **Inputs**: backend, Qdrant, migrations, Bruno collection.
- **Outputs**: evidencias de validacao completa.

## Constraints & Rules

1. Toda rota nova deve ter request Bruno.
2. Nenhuma regressao nos testes dos stages anteriores.

## Implementation Checklist

- [ ] Rodar `pytest`.
- [ ] Rodar `validate_openapi.py`.
- [ ] Rodar `validate_tasks.py`.
- [ ] Conferir `genai-endpoints/TenantCollections/` contra rotas novas.
- [ ] Registrar pendencias residuais.

## Acceptance Criteria

- [ ] Pytest passa sem falhas.
- [ ] OpenAPI valido.
- [ ] Tasks validadas.
- [ ] Bruno cobre collections e documents.

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

- **Risks**: falha no worker de indexacao bloqueia todo o RAG.
- **Rollback**: manter Stage 06 aberto e bloquear stages dependentes.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para verificacao final do Stage 06.
