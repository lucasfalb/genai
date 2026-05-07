# Stage 04 Tasks - Execution Engine, SSE e Redis Lock

| ID | Task | Status | Priority | Depends On |
| :--- | :--- | :--- | :--- | :--- |
| TASK-019 | [Agent State e Run Bootstrap](task_019_agent_state_run_bootstrap.md) | COMPLETED | CRITICAL | TASK-015 |
| TASK-020 | [Redis Session Lock](task_020_redis_session_lock.md) | COMPLETED | CRITICAL | TASK-005 |
| TASK-021 | [Executor Basico e Persistencia de Mensagens](task_021_basic_executor_message_persistence.md) | COMPLETED | CRITICAL | TASK-019, TASK-020 |
| TASK-022 | [Endpoint Chat SSE](task_022_chat_sse_endpoint.md) | COMPLETED | HIGH | TASK-021 |
| TASK-023 | [Base Graph LangGraph](task_023_base_graph_langgraph.md) | COMPLETED | HIGH | TASK-019 |
| TASK-024 | [Validacao Stage 04](task_024_stage_04_verification.md) | COMPLETED | HIGH | TASK-022, TASK-023 |

## Scope

Estas tasks cobrem o Stage 04 definido em `docs/stages/stage_04_engine.md`: bootstrap de run, estado do agente, lock Redis por sessao, endpoint de chat com SSE, persistencia de mensagens e base para grafo de execucao.

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

## Notes

- O endpoint SSE deve exigir `X-Tenant-ID`, Bearer token e permissao `INTERACT_WITH_AGENTS`.
- O lock Redis deve serializar execucoes por `tenant_id` e `session_id`, retornando conflito quando ja existir run ativo.
- A primeira entrega do executor usa resposta deterministica local; integracao LLM real fica para os stages de provider/prompt/RAG.
