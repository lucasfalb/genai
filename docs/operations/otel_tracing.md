# OpenTelemetry Tracing

## Arquitetura

```text
FastAPI (auto-instrumentation + manual spans)
  | OTLP gRPC (port 4317)
  v
otel-collector (receives OTLP, batches, exports)
  | OTLP gRPC (internal: tempo:4317)
  v
Tempo (trace storage + query API - http://localhost:3200)
  |
  v
Grafana (Tempo datasource + dashboard - http://localhost:3000)
```

## Servicos

| Servico | Container | Porta |
|---------|-----------|-------|
| OTel Collector | `genai-otel-collector` | `4317` (gRPC, localhost) |
| Tempo | `genai-tempo` | `3200` (HTTP API, localhost) |
| Grafana | `genai-grafana` | `3000` (UI, localhost) |

## Como Validar O Pipeline Completo

### 1. Subir a stack

```bash
docker compose up -d otel-collector tempo grafana
```

### 2. Verificar collector

```bash
docker compose logs otel-collector --tail 5
# Deve mostrar que o collector iniciou e esta processando dados.
```

### 3. Verificar Tempo

```bash
curl http://localhost:3200/ready
```

### 4. Verificar traces no Grafana

1. Abrir http://localhost:3000 (acesso anonimo)
2. Ir em "Explore" e selecionar datasource "Tempo"
3. Consultar TraceQL: `{ resource.service.name = "genai-platform" }`
4. Executar um request no backend para gerar spans, por exemplo `GET /healthz`

### 5. Verificar dashboard de workflows

1. Abrir http://localhost:3000/d/genai-workflow-telemetry/genai-workflow-telemetry
2. Confirmar que o dashboard "GenAI Workflow Telemetry" carregou
3. Usar os paineis do topo para traces HTTP, erros, `graph.run`, `llm.call` e `rag.retrieve`
4. Usar as secoes de workflow para acompanhar fluxos completos como criacao de conta, criacao de agente, execucao de chat, onboarding de tenant e base de conhecimento
5. Usar os paineis por endpoint dentro de cada workflow para filtrar traces por `http.route` + `http.method`

O dashboard e provisionado automaticamente em `grafana/dashboards/agent-traces.json`. Ele e gerado a partir das rotas FastAPI registradas e atualmente cobre 90 operacoes agrupadas em 10 workflows: plataforma/publico, conta/autenticacao, administracao superadmin, configuracao superadmin, onboarding/membros, criacao/configuracao de agente, execucao de agente, registry, settings de IA e conhecimento/RAG.

## Spans De Dominio

| Span | Local | Atributos |
|------|-------|-----------|
| `graph.run` | `executor.py:start_stream()` | instance_id, tenant_id, model |
| `llm.call` | `base_graph.py:llm_node()` | gen_ai.request.model, gen_ai.system, temperature, gen_ai.usage.* |
| `tool.execute` | `base_graph.py:dispatch_node()` | tool_name, executor, success |
| `handoff.resolve` | `base_graph.py:handoff_node()` | target_instance_id |
| `rag.retrieve` | `nodes/rag_node.py` | collection_count, query_length, chunk_count, max_score |

## Configuracao

Variaveis de ambiente para OTel:

| Variavel | Default | Descricao |
|----------|---------|-----------|
| `OTEL_SERVICE_NAME` | `genai-platform` | Nome do servico nos traces |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | Endpoint OTLP gRPC |
| `OTEL_RESOURCE_ATTRIBUTES` | `""` | Atributos extras, ex: `env=prod,region=us` |
| `GENAI_ENV` | `development` | Ambiente |

Para backend rodando direto no host (`uvicorn app.main:app`), use `http://localhost:4317`.
Para backend rodando dentro do Docker Compose, use `http://otel-collector:4317`.
O app normaliza `otel-collector` para `localhost` quando detecta execucao fora de container, evitando erros `StatusCode.UNAVAILABLE` em dev local.

## Troubleshooting

**Nenhum trace aparece no Grafana?**
1. Verificar se `otel-collector` e `tempo` estao rodando: `docker compose ps otel-collector tempo`
2. Verificar logs do collector: `docker compose logs otel-collector --tail 20`
3. Verificar se o backend esta configurado com `OTEL_EXPORTER_OTLP_ENDPOINT` correto
4. Fazer um request de chat ou `GET /healthz` para gerar traces

**Erro `StatusCode.UNAVAILABLE` exportando para `otel-collector:4317`?**
Isso geralmente significa que o backend esta rodando no host, mas recebeu endpoint de Docker DNS. Reinicie o backend depois de ajustar `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`, ou remova o override do shell para o app ler o `.env`.

**Porta 4317 ja esta em uso?**
O collector mapeia `127.0.0.1:4317` para o host. Se houver conflito, alterar a porta no `docker-compose.yml` e no `OTEL_EXPORTER_OTLP_ENDPOINT`.
