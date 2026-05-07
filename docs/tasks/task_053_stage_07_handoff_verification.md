# Task: TASK-053 - Verificacao Stage 07 Handoff

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-053 |
| **Group** | HANDOFF |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_07_handoff.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Antes de avancar para canais, o pipeline de hand-off completo precisa estar validado: migration, CRUD de links, tool fantasma no bootstrap, handoff_node, sanitizacao de historico e router classifier.

## Objectives

- [ ] Executar suite pytest completa.
- [ ] Executar validador OpenAPI.
- [ ] Executar validador de tasks.
- [ ] Verificar cobertura Bruno para endpoints de agent_links.
- [ ] Confirmar que historico nao vaza instrucoes do agente de origem.

## Non-Goals

- Teste de latencia do router.
- Validacao de qualidade do HandoffSummary.

## Stage Boundaries

Validacao somente do Stage 07 e regressao dos stages anteriores.

## Dependencies

- TASK-049, TASK-051, TASK-052

## Inputs & Contracts

- **Inputs**: backend, migrations, Bruno collection e scripts de validacao.
- **Outputs**: evidencias de validacao completa.
- **Schemas**: OpenAPI e arquivos `.bru`.

## Constraints & Rules

1. Toda rota nova deve ter request Bruno.
2. Nenhuma regressao nos testes dos stages anteriores.
3. Historico do agente de origem nao deve vazar para o agente destino.

## Implementation Checklist

- [ ] Rodar `pytest`.
- [ ] Rodar `validate_openapi.py`.
- [ ] Rodar `validate_tasks.py`.
- [ ] Conferir `genai-endpoints/TenantAgentLinks/` contra rotas novas.
- [ ] Registrar pendencias residuais.

## Acceptance Criteria

- [ ] Pytest passa sem falhas.
- [ ] OpenAPI valido.
- [ ] Tasks validadas.
- [ ] Bruno cobre agent_links CRUD.

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

- **Risks**: loop de hand-off entre instancias pode travar o grafo.
- **Rollback**: manter Stage 07 aberto e bloquear Stage 08.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para verificacao final do Stage 07.
