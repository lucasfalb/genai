# Task: TASK-022 - Endpoint Chat SSE

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-022 |
| **Group** | ENGINE |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_04_engine.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O Stage 04 expõe execucao por chat em streaming SSE para API, widget e canais futuros.

## Objectives

- [x] Criar endpoint `POST /api/v1/agent/instances/{instance_id}/chat`.
- [x] Retornar `text/event-stream`.
- [x] Documentar endpoint no OpenAPI.
- [x] Cancelar run quando cliente desconectar.

## Non-Goals

- Implementar auth por agent API key de canais.
- Implementar UI de chat.

## Stage Boundaries

Esta task cobre apenas endpoint HTTP/SSE do Stage 04 usando auth tenant existente.

## Dependencies

- TASK-021

## Inputs & Contracts

- **Inputs**: `ChatRequest` com mensagem e session id opcional.
- **Outputs**: eventos SSE serializados.
- **Schemas**: request/response documentados no OpenAPI.

## Constraints & Rules

1. Endpoint deve exigir Bearer token e `X-Tenant-ID`.
2. Endpoint deve exigir permissao `INTERACT_WITH_AGENTS`.
3. Conflito de lock deve retornar `409`.

## Implementation Checklist

- [x] Criar schemas de chat.
- [x] Criar rota FastAPI.
- [x] Integrar executor.
- [x] Adicionar validacao OpenAPI.
- [x] Testar cancelamento por disconnect.

## Acceptance Criteria

- [x] Endpoint retorna eventos SSE validos.
- [x] Endpoint persiste sessao e mensagens.
- [x] Endpoint retorna `409` para sessao bloqueada.
- [x] OpenAPI valida rota protegida.

## Verification

```bash
pytest tests/test_stage_04_engine.py
backend\.venv\Scripts\python scripts\validate_openapi.py
```

## Risks & Rollback

- **Risks**: streaming mal documentado pode quebrar consumidores HTTP.
- **Rollback**: remover roteador de agent chat ate concluir executor.

## Execution Log

- `[2026-05-07 14:20]`: Task criada a partir do Stage 04.
- `[2026-05-07 14:35]`: Endpoint SSE implementado e validado em OpenAPI; cancelamento por disconnect segue pendente.
- `[2026-05-07 15:10]`: Endpoint passou a preparar o run antes do response, manter lock/conexao durante streaming e cancelar em disconnect.
