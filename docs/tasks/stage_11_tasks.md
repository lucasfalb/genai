# Stage 11 Tasks - OpenTelemetry & Tempo Tracing

| ID | Task | Status | Priority | Depends On |
| :--- | :--- | :--- | :--- | :--- |
| TASK-080 | [OTel SDK Bootstrap & Auto-Instrumentation](task_080_otel_sdk_bootstrap.md) | IN_PROGRESS | HIGH | - |
| TASK-081 | [OTel Collector & Tempo in Docker Compose](task_081_otel_collector_tempo.md) | IN_PROGRESS | HIGH | TASK-080 |
| TASK-082 | [Manual Tracing in Engine](task_082_manual_tracing_engine.md) | IN_PROGRESS | MEDIUM | TASK-080 |
| TASK-083 | [Grafana Dashboards & E2E Verification](task_083_grafana_dashboards.md) | IN_PROGRESS | MEDIUM | TASK-080, TASK-081, TASK-082 |

## Scope

Estas tasks cobrem o Stage 10b definido em `docs/stages/stage_10b_otel_observability.md`: implementar tracing distribuido OpenTelemetry no backend FastAPI, configurar collector + Tempo + Grafana, e adicionar spans manuais no motor de execucao do agente.

## Implementation Order

1. TASK-080 - Deps Python + `otel.py` + auto-instrumentation no `main.py`.
2. TASK-081 - OTel Collector + Tempo no `docker-compose.yml`.
3. TASK-082 - Spans manuais no engine (executor, LLM, tools, handoff, RAG).
4. TASK-083 - Grafana + dashboards + documentacao + validacao E2E.

## Notes

- OTel SDK deve tolerar ausencia do collector (app nao quebra se OTLP endpoint estiver offline).
- Dados sensiveis nunca em span attributes - usar `_redact()` do run_trace como referencia.
- Versao dev usa Tempo com storage local efemero.
- Grafana datasource Tempo provisionado automaticamente via arquivo YAML.
