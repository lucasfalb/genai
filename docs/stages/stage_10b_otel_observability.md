# Stage 10b - OpenTelemetry & Tempo Tracing

## Objetivo

Implementar tracing distribuido padrao OpenTelemetry (OTel) na plataforma: instrumentar o backend FastAPI com auto-instrumentation OTel, adicionar spans manuais no motor de execucao de agentes, configurar o OpenTelemetry Collector para receber e rotear traces, e entregar visualizacao via Tempo + Grafana.

## Escopo do Stage

- Adicionar dependencias Python `opentelemetry-*` no `pyproject.toml`.
- Criar `backend/app/otel.py` com inicializacao do `TracerProvider`, `BatchSpanProcessor`, OTLP exporter e `Resource`.
- Aplicar auto-instrumentation FastAPI no `main.py`.
- Instrumentar chamadas a banco (asyncpg), cache (redis) e HTTP client (httpx) via auto-instrumentation.
- Adicionar spans manuais no `engine/executor.py` (execucao do grafo), `engine/base_graph.py` (LLM/tools/handoff) e `engine/nodes/rag_node.py`.
- Adicionar servicos `otel-collector`, `tempo` e `grafana` no `docker-compose.yml`.
- Configurar pipeline OTLP: FastAPI -> OTel Collector -> Tempo.
- Criar datasource Tempo no Grafana e dashboard basico de traces.
- Verificar end-to-end: requisitar backend e ver trace aparecendo no Grafana Explore.

## Fora De Escopo

- Metrica Prometheus (deferida para Stage 10c ou futuro).
- Frontend RUM (Real User Monitoring) com OTel.
- Exportacao de traces para terceiros (Datadog, New Relic, etc.).
- Trace entre servicos diferentes (ainda so existe o backend Python).
- Logs estruturados via OTel (Loki ou similar).

## Privacidade & Seguranca

- Atributos sensiveis (`ai_api_key`, `api_key_encrypted`, `authorization`, `password`, `secret`, `token`) nunca devem ser incluidos em span attributes.
- Usar `tracer.set_attribute` apenas com dados de dominio nao-sensiveis (instance_id, tenant_id, model_name, token_count, etc.).
- O `_redact()` existente em `engine/run_trace.py` continua sendo o unico responsavel por sanitizar payloads do trace custom.

## Arquitetura

```text
FastAPI (auto-instrumentation + manual spans)
  | OTLP gRPC
  v
otel-collector (receives OTLP, batches, exports)
  | OTLP gRPC
  v
Tempo (trace storage + query API)
  |
  v
Grafana (datasource Tempo + Explore)
```

## Componentes

| Camada | Item |
| :--- | :--- |
| Deps Python | `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `-asyncpg`, `-redis`, `-httpx`, `opentelemetry-exporter-otlp-proto-grpc` |
| Backend | `backend/app/otel.py` - TracerProvider + BatchSpanProcessor + OTLP exporter |
| Backend | `backend/app/main.py` - inicializacao OTel |
| Backend | `backend/engine/executor.py` - spans manuais no grafo |
| Backend | `backend/engine/base_graph.py` - spans manuais no LLM, tools e handoff |
| Backend | `backend/engine/nodes/rag_node.py` - span manual no RAG |
| Backend | `backend/engine/run_trace.py` - bridge `otel_trace_id` para o trace custom |
| Infra | `otel-collector` (contrib) no docker-compose |
| Infra | `tempo` (Tempo) no docker-compose |
| Infra | `grafana` no docker-compose |

## Dependencias

- Stage 04 (engine + executor) - para spans manuais no grafo.
- Stage 10 (run traces) - reuso de `_redact()` e conhecimento dos fluxos de execucao.
