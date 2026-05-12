# Task: TASK-080 - OTel SDK Bootstrap & Auto-Instrumentation

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-080 |
| **Group** | OBSERVABILITY |
| **Status** | IN_PROGRESS |
| **Stage Ref** | `docs/stages/stage_10b_otel_observability.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-12 |
| **Updated At** | 2026-05-12 |

## Context

O backend FastAPI nao possui qualquer instrumentacao OpenTelemetry. O stack do projeto lista OTel na camada de observabilidade mas nenhum codigo ou dependencia existe. Esta task implementa a camada base: dependencias Python, inicializacao do SDK OTel (TracerProvider, BatchSpanProcessor, OTLP exporter) e auto-instrumentation para FastAPI, asyncpg, redis e httpx.

## Objectives

- [x] Adicionar pacotes `opentelemetry-*` no `backend/pyproject.toml`.
- [x] Criar `backend/app/otel.py` com `TracerProvider`, `BatchSpanProcessor`, `OTLPSpanExporter` e `Resource` configurados via environment variables.
- [ ] Configurar `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT` e `OTEL_RESOURCE_ATTRIBUTES` como defaults no `.env` e sobrescritaveis por env vars.
- [x] Adicionar startup hook no `backend/app/main.py` para inicializar OTel e aplicar `FastAPIInstrumentor`.
- [~] Verificar que spans de HTTP request (FastAPI), database (asyncpg), cache (redis) e HTTP client (httpx) sao gerados e exportados via OTLP.

## Non-Goals

- Instrumentacao manual de negocios (executor, LLM node) - task TASK-082.
- Configuracao de collector ou backend de tracing - task TASK-081.
- Dashboards Grafana - task TASK-083.

## Stage Boundaries

Implementacao restrita ao `backend/` - dependencias Python, `otel.py`, `main.py` e env vars. Nao modifica docker-compose nem frontend.

## Dependencies

- Nenhuma (primeira task do Stage 10b).

## Inputs & Contracts

- **Inputs**: env vars `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_RESOURCE_ATTRIBUTES`.
- **Outputs**: spans OTel exportados via OTLP gRPC para o endpoint configurado.
- **Schemas**: nenhum schema Pydantic novo. `Resource` OTel com `service.name`, `deployment.environment`, `service.version`.

## Constraints & Rules

1. **Nao quebrar startup**: se OTel falhar (exemplo: collector indisponivel), o app deve iniciar sem crash - usar `BatchSpanProcessor` com `on_error` callback nao-bloqueante ou try/except no setup.
2. **Nao expor dados sensiveis**: span attributes nunca devem conter api keys, tokens ou secrets - apenas metadados de rota, tenant_id, instance_id, status code, duration.
3. **Configuravel via env**: todo endpoint, servico e resource attribute deve vir de env vars, nunca hardcoded.
4. **Auto-instrumentation padrao**: usar `FastAPIInstrumentor.instrument_app()`, `AsyncpgInstrumentor()`, `RedisInstrumentor()`, `HttpxInstrumentor()`.
5. **Versionamento**: `OTEL_SERVICE_NAME` = `genai-platform`, version extraida do `pyproject.toml`.

## Implementation Checklist

- [~] Adicionar deps no `backend/pyproject.toml` e rodar `pip install`.
- [x] Criar `backend/app/otel.py` com funcao `setup_otel()` chamada no startup.
- [x] Em `setup_otel()`: criar `Resource`, `TracerProvider`, `BatchSpanProcessor` com `OTLPSpanExporter`, setar tracer provider global.
- [x] Instrumentar FastAPI, asyncpg, redis, httpx.
- [x] Adicionar hook `startup` no `main.py` que chama `setup_otel()`.
- [ ] Configurar env vars default no `.env` apontando para `otel-collector:4317`.
- [x] Testar que spans HTTP chegam ao collector e aparecem no Tempo/Grafana.
- [x] Verificar que app sobe sem erros com collector indisponivel.

## Acceptance Criteria

- [ ] `pip install` com as novas deps completa sem erros.
- [ ] Ao iniciar o backend, logs indicam `OTel SDK initialized` e spans comecam a ser gerados.
- [x] Cada request HTTP ao FastAPI gera um span com `http.method`, `http.route`, `http.status_code`.
- [ ] Queries ao PostgreSQL geram spans com `db.system`, `db.statement` (truncado).
- [ ] Comandos Redis geram spans com `db.system=redis`.
- [ ] App inicializa sem crash quando nenhum collector OTel esta disponivel.

## Verification

```bash
docker compose up -d otel-collector
cd backend
.venv\Scripts\python -m pytest tests/ -x -q -k "otel or tracing"
# Verificar logs:
# "OTel SDK initialized"
# "Span exported: POST /agent/instances/{id}/chat"
```

## Risks & Rollback

- **Risco**: Instrumentacao adicionar latencia em cold start. Mitigacao: `BatchSpanProcessor` com fila em background, timeout configurado.
- **Risco**: Vazamento de dados sensiveis em span attributes. Mitigacao: revisao de todos `set_attribute` e uso de `_redact()` onde aplicavel.
- **Rollback**: Remover linhas do `main.py`, deps do `pyproject.toml` e arquivo `otel.py`.

## Execution Log

- `[2026-05-12 09:00]`: Task criada a partir do planejamento Stage 10b.
- `[2026-05-12 14:00]`: Adicionadas deps opentelemetry-* no pyproject.toml.
- `[2026-05-12 14:10]`: Criado backend/app/otel.py com setup_otel() - TracerProvider, BatchSpanProcessor, OTLP exporter, FastAPIInstrumentor, AsyncPGInstrumentor, RedisInstrumentor, HTTPXClientInstrumentor.
- `[2026-05-12 14:15]`: Corrigido nome dos instrumentors (AsyncpgInstrumentor -> AsyncPGInstrumentor, HttpxInstrumentor -> HTTPXClientInstrumentor).
- `[2026-05-12 14:20]`: Wire up OTel no main.py via lifespan handler.
- `[2026-05-12 14:25]`: Verificado que app sobe sem erros com collector offline.
- `[2026-05-12 15:35]`: Revisado setup OTel: trocado SimpleSpanProcessor por BatchSpanProcessor, adicionado service.version quando disponivel e idempotencia no setup.
- `[2026-05-12 17:45]`: Validacao operacional encontrou que `setup_otel()` no lifespan era tarde demais para spans HTTP; inicializacao movida para montagem do app.
- `[2026-05-12 17:50]`: Confirmado no backend de traces: servico `genai-platform` listado e traces `GET /healthz` recebidos via collector.
