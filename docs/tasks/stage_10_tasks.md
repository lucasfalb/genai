# Stage 10 Tasks - Observability & Debug Playground

| ID | Task | Status | Priority | Depends On |
| :--- | :--- | :--- | :--- | :--- |
| TASK-077 | [Run Trace Capture & SSE Emission](task_077_backend_run_trace_capture.md) | COMPLETED | HIGH | TASK-039, TASK-046 |
| TASK-078 | [Frontend Debug Panel (Run Trace Inspector)](task_078_frontend_debug_panel.md) | COMPLETED | HIGH | TASK-074, TASK-077 |
| TASK-079 | [Per-Instance Constraints (Backend + Frontend)](task_079_constraints_per_instance.md) | COMPLETED | HIGH | TASK-037, TASK-064 |

## Scope

Estas tasks cobrem o Stage 10 definido em `docs/stages/stage_10_observability.md`: persistir trace por run no backend, expor via SSE + REST, e renderizar painel "Debug" no frontend para o tenant inspecionar prompt montado, chunks RAG, tool calls e hand-offs.

## Implementation Order

1. Migration `agent_run_traces` + repository.
2. `engine/run_trace.py` (builder + redaction de campos sensiveis).
3. `engine/executor.py` consolida trace, persiste e emite evento SSE `run.trace`.
4. Endpoints GET (`runs/latest`, `runs/{run_id}`, `runs`) tenant-scoped.
5. Frontend: tipos + tracesApi + handler `onTrace` no chat.ts.
6. Frontend: componente `RunTracePanel` + rota `/instances/{id}/debug` + tab "Debug" no layout.

## Notes

- Trace nunca contem `ai_api_key` / `authorization` / `secret` / `token` — sanitizados em `_redact`.
- Trace persistido tem FK ON DELETE CASCADE para `tenants(id)`.
- SSE event `run.trace` chega antes de `run.completed`; chat client pode usar ou ignorar.
- Debug panel e independente do chat — funciona com `chatSession.getLastRunId()` ou fallback `runs/latest`.
