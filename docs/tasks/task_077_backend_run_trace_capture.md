# Task: TASK-077 - Run Trace Capture & SSE Emission

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-077 |
| **Group** | OBSERVABILITY |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_10_observability.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Codex |
| **Created At** | 2026-05-10 |
| **Updated At** | 2026-05-10 |

## Context

A spec define que cada execucao do agente emita um trace com prompt montado, chunks RAG, tools chamadas, hand-offs e tempo de execucao. O backend ja carrega esses dados em `AgentState`, mas nao os expoe ao client nem persiste para inspecao posterior. Esta task captura o snapshot do run, persiste em `agent_run_traces` e emite via SSE.

## Objectives

- [x] Criar tabela `agent_run_traces` (run_id, tenant_id, instance_id, session_id, channel, trace JSONB, started_at, completed_at, created_at).
- [x] Criar repository `RunTraceRepository` com `create`, `get`, `get_latest_by_session`, `list_by_session`, `list_by_instance`, `list_by_tenant`.
- [x] Adicionar `system_prompt_sections` ao `AgentState` e popular no `RunBootstrap`.
- [x] Construir `engine/run_trace.py` com `build_run_trace()` montando payload sanitizado a partir de bootstrap state + result state.
- [x] Sanitizar campos sensiveis (`ai_api_key`, `authorization`, `password`, `secret`, `token`, `api_key_encrypted`).
- [x] Em `AgentExecutor.start_stream`: medir started_at/completed_at, montar trace, persistir, retornar via `AgentRunStream`.
- [x] Emitir evento SSE `run.trace` antes de `run.completed`, com payload no `metadata.trace`.
- [x] Adicionar endpoints GET tenant-scoped por instancia: `runs/latest`, `runs/{run_id}`, `runs` (lista).
- [x] Adicionar endpoint GET tenant-scoped agregado: `GET /api/v1/agent/runs`.
- [x] Adicionar schemas `RunTraceResponse`, `RunTraceListItem`.
- [x] Atualizar testes do executor para esperar 4 eventos (`message.persisted`, `assistant.delta`, `run.trace`, `run.completed`).

## Non-Goals

- Streaming token a token do LLM (assistant.delta single-shot mantido).
- Latencia por no LangGraph individual.
- Metricas Prometheus.
- Hooks por nó internos do graph.

## Stage Boundaries

Apenas captura, persistencia e exposicao do trace por run. Nao implementa dashboards, metricas ou analytics multi-tenant.

## Dependencies

- TASK-039 (LLM node + provider integration)
- TASK-046 (RAG node integration — fornece `retrieved_chunks`)

## Inputs & Contracts

- **Migration**: `20260510_0015_agent_run_traces.py`.
- **Repository**: `database/repositories/run_traces.py`.
- **Builder**: `engine/run_trace.py` com `build_run_trace(...)` e `_redact()`.
- **State**: campo `system_prompt_sections: dict` em `AgentState`.
- **SSE event**: `{"event":"run.trace","session_id":"<uuid>","sequence_no":N,"metadata":{"run_id":"<uuid>","trace":{...}}}`.
- **Endpoints**:
  - `GET /api/v1/agent/instances/{id}/runs/latest?session_id=<uuid>`
  - `GET /api/v1/agent/instances/{id}/runs/{run_id}`
  - `GET /api/v1/agent/instances/{id}/runs?session_id=<uuid>&limit=20`
  - `GET /api/v1/agent/runs?limit=100`
- **Schemas**: `RunTraceResponse`, `RunTraceListItem`.

## Constraints & Rules

1. Trace nunca contem `ai_api_key`, `authorization`, `password`, `secret`, `token`, `api_key_encrypted`.
2. Tabela cascade-delete por `tenant_id` ON DELETE CASCADE.
3. Endpoints exigem `Permission.MANAGE_AGENT_INSTANCES` (tenant-scoped).
4. Endpoints rejeitam (404) trace cuja `instance_id` nao bate com a rota — protege cross-instance.
5. Falha ao persistir trace propaga (nao silenciada) — bug de schema deve falhar visivelmente.
6. Builder usa `datetime.now(timezone.utc)` antes do bootstrap e depois do `graph.ainvoke`.
7. `metadata.trace` no SSE eh exatamente o mesmo dict persistido, ja sanitizado.

## Implementation Checklist

- [x] Migration `20260510_0015_agent_run_traces` (down_revision `6ace8bb1b085`).
- [x] Repository com 5 metodos + `_from_row` helper.
- [x] `engine/state.py` campo `system_prompt_sections: dict`.
- [x] `engine/bootstrap.py` popula sections a partir de `SystemPrompt`.
- [x] `engine/run_trace.py` com `build_run_trace`, `_redact`, normalizadores de chunk/tool.
- [x] `engine/executor.py` mede tempo, monta trace, persiste, emite SSE.
- [x] `app/schemas.py` `RunTraceResponse`, `RunTraceListItem`, `RunTraceSection`.
- [x] `api/v1/agent.py` endpoints GET por instancia.
- [x] `api/v1/agent.py` endpoint agregado `GET /agent/runs` para dashboard tenant-level.
- [x] Test `test_agent_executor_persists_messages_in_order` ajustado para 4 eventos + asserts no trace.

## Acceptance Criteria

- [x] Run insere linha em `agent_run_traces` com `trace` JSONB nao-vazio.
- [x] SSE stream emite `run.trace` antes de `run.completed`.
- [x] `GET /runs/latest` retorna trace mais recente do (instance, session) filtrados.
- [x] `GET /runs/{run_id}` retorna 404 se `instance_id` na rota nao bate com o trace.
- [x] `GET /agent/runs` lista traces recentes do tenant com `total_tokens`, `prompt_tokens`, `completion_tokens`, `embedding_tokens` e `embedding_calls`.
- [x] Trace nao contem `ai_api_key` em qualquer nivel (verificado em test).
- [x] Migration aplica em DB de teste e dev (`alembic upgrade head`).

## Verification

```bash
cd backend
SYNC_DATABASE_URL=postgresql+psycopg://genai:genai@localhost:5432/genai_test .venv/Scripts/alembic upgrade head
.venv/Scripts/python -m pytest tests/test_stage_04_engine.py tests/test_stage_05_ai_provider.py tests/test_stage_06_documents.py -q
# manual: curl POST /agent/instances/{id}/chat e inspecionar evento run.trace
```

## Risks & Rollback

- **Risco**: trace JSON gigante em conversas longas (system_prompt + chunks). Mitigacao: chunks normalizados sem dropar texto, mas duracao_ms permite identificar runs lentos.
- **Risco**: redacao recursiva pode esconder campos legitimos cujo nome colide com SENSITIVE_KEYS. Mitigacao: lista pequena e especifica, validada em test.
- **Rollback**: `alembic downgrade 6ace8bb1b085` + revert dos arquivos `engine/run_trace.py`, `database/repositories/run_traces.py`, alteracoes em `executor.py`/`bootstrap.py`/`state.py`/`agent.py`. Frontend nao quebra (404 vira UI vazia).

## Execution Log

- `[2026-05-10 02:00]`: Task criada como parte do Stage 10.
- `[2026-05-10 02:05]`: Migration + repository + tabela `agent_run_traces` criados.
- `[2026-05-10 02:10]`: `system_prompt_sections` adicionado ao state; bootstrap popula a partir de `SystemPrompt`.
- `[2026-05-10 02:20]`: `engine/run_trace.py` builder + redaction.
- `[2026-05-10 02:25]`: `executor.py` mede tempo, monta trace, persiste, emite SSE `run.trace`.
- `[2026-05-10 02:30]`: 3 endpoints GET adicionados em `api/v1/agent.py` com permissao tenant-scoped.
- `[2026-05-10 02:35]`: Test `test_agent_executor_persists_messages_in_order` atualizado para 4 eventos. 19 tests passando.
- `[2026-05-10 02:40]`: Migration aplicada nos DBs `genai` e `genai_test`. Status -> COMPLETED.
- `[2026-05-12 19:30]`: Endpoint agregado `GET /api/v1/agent/runs` adicionado para alimentar dashboard tenant-level de tokens em Observability.
