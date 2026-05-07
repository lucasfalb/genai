# Task: TASK-057 - Canal API com SSE e Canal Widget

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-057 |
| **Group** | CHANNELS |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_08_channels.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O canal API expoe `POST /api/v1/chat` autenticado por `X-Agent-Key` com resposta SSE. O canal Widget e um script embeddavel que valida `allowed_origins`. Ambos usam `SessionManager` para normalizar entrada e `ResponseManager` para finalizar.

## Objectives

- [ ] Criar endpoint `POST /api/v1/chat` autenticado por `X-Agent-Key`.
- [ ] Integrar `SessionManager.normalize(channel='api', ...)` e `SessionLock`.
- [ ] Retornar SSE stream de eventos (token a token ou evento final).
- [ ] Validar `allowed_origins` para requisicoes de widget (header `Origin`).
- [ ] Testar: chat com key valida, key invalida 401, 409 com sessao duplicada.

## Non-Goals

- Script de embed do widget (frontend).
- Webhook e WhatsApp (TASK-058).

## Stage Boundaries

Apenas endpoints de canal API e Widget. O grafo LangGraph ja existe.

## Dependencies

- TASK-056 (SessionManager, ResponseManager, verify_agent_api_key)

## Inputs & Contracts

- **Inputs**: `X-Agent-Key`, `{message: str, session_id: str}`.
- **Outputs**: SSE stream com eventos `{type: token, content: ...}` e `{type: done}`.
- **Schemas**: `ChatRequest(message, session_id)`.

## Constraints & Rules

1. `X-Agent-Key` verificado via hash; 401 se invalida.
2. `SessionLock` adquirido antes de iniciar run; 409 se ja existir execucao ativa.
3. Widget valida `Origin` contra `allowed_origins` do canal; 403 se nao permitido.
4. SSE headers: `Cache-Control: no-cache`, `X-Accel-Buffering: no`.

## Implementation Checklist

- [ ] Criar `api/v1/agent/chat.py` com endpoint SSE usando `X-Agent-Key`.
- [ ] Integrar `SessionLock`, `SessionManager` e `ResponseManager`.
- [ ] Adicionar validacao de `allowed_origins` para canal `widget`.
- [ ] Registrar router em `app/main.py`.
- [ ] Testar: key valida streaming, key invalida, sessao concorrente 409, widget origin invalida.

## Acceptance Criteria

- [ ] `POST /api/v1/chat` com key valida retorna SSE.
- [ ] Key invalida retorna 401.
- [ ] Sessao duplicada retorna 409.
- [ ] Widget com origin invalida retorna 403.

## Verification

```bash
cd backend
pytest tests/test_stage_08_api_channel.py
```

## Risks & Rollback

- **Rollback**: desabilitar endpoint `/api/v1/chat` no router.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para canal API SSE e canal Widget.
