# Stage 10 - Observability & Debug Playground

## Objetivo

Materializar a secao **10. Observabilidade** do `docs/platform_technical_spec.md` na superficie do produto: capturar e expor o trace de cada execucao do agente para que tenants possam inspecionar reasoning, prompt montado, RAG, tool calls e hand-offs.

## Escopo do Stage

- Persistir trace por execucao (`agent_run_traces`).
- Emitir evento SSE `run.trace` no fim de cada run, com payload sanitizado.
- Endpoints GET tenant-scoped para latest/by-id/list.
- Aba "Debug" no detalhe da instancia (`/app/{tenant}/instances/{id}/debug`).
- Painel `RunTracePanel` consumindo o trace mais recente da sessao ativa, com fallback para o ultimo run da instancia.

## Fora de escopo

- Coleta de metricas Prometheus (deferido para Stage 10b).
- Latencia por no individual do LangGraph (graph nao expoe hooks finos no MVP).
- Streaming token a token do LLM (assistant.delta hoje e single-shot).
- Dashboards multi-tenant (analytics) — tarefa de produto futura.

## Privacidade & Seguranca

- `ai_api_key`, `api_key_encrypted`, `authorization`, `password`, `secret`, `token` jamais entram no trace persistido nem no SSE — sanitizados em `engine/run_trace.py:_redact`.
- Acesso ao trace exige `Permission.MANAGE_AGENT_INSTANCES` no tenant atual.
- Trace e cascade-deleted via FK `tenants(id) ON DELETE CASCADE`.

## Componentes

| Camada | Item |
| :--- | :--- |
| DB | Migration `20260510_0015_agent_run_traces` + tabela `agent_run_traces` |
| Repo | `database/repositories/run_traces.py` |
| Engine | `engine/run_trace.py` (builder + redaction) |
| Engine | `engine/state.py` (`system_prompt_sections`) |
| Engine | `engine/bootstrap.py` (popula sections) |
| Engine | `engine/executor.py` (build + persist + emit SSE) |
| API | `GET /agent/instances/{id}/runs/latest` |
| API | `GET /agent/instances/{id}/runs/{run_id}` |
| API | `GET /agent/instances/{id}/runs` |
| Schema | `RunTraceResponse`, `RunTraceListItem` |
| Frontend | `lib/api/types.ts` (RunTrace*) |
| Frontend | `lib/api/chat.ts` (`onTrace`, `tracesApi`) |
| Frontend | `lib/components/instance/run-trace-panel.svelte` |
| Frontend | route `/instances/{id}/debug/+page.svelte` |
| Frontend | layout tab "Debug" |

## Dependencias

- Stage 04 (engine + executor)
- Stage 05 (instance config, prompt builder)
- Stage 06 (RAG retriever — chunks aparecem no trace quando habilitados)
