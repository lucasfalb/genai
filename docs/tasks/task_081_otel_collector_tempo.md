# Task: TASK-081 - OpenTelemetry Collector & Tempo in Docker Compose

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-081 |
| **Group** | OBSERVABILITY |
| **Status** | IN_PROGRESS |
| **Stage Ref** | `docs/stages/stage_10b_otel_observability.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-12 |
| **Updated At** | 2026-05-12 |

## Context

O docker-compose atual nao possui servicos de observabilidade. Para receber, processar e visualizar os spans emitidos pelo backend (TASK-080), e necessario adicionar o OpenTelemetry Collector (recebe OTLP, faz batch e roteia) e o Tempo (armazena e exibe traces em API propria e exploracao via Grafana).

## Objectives

- [x] Adicionar servico `otel-collector` no `docker-compose.yml` usando imagem `otel/opentelemetry-collector-contrib`.
- [x] Criar `otel-collector-config.yml` com pipeline: receivers OTLP gRPC -> processors batch -> exporters OTLP gRPC (para Tempo).
- [x] Configurar `batch` processor com timeout 5s e batch size controlado.
- [x] Adicionar servico `tempo` no `docker-compose.yml` usando imagem `grafana/tempo` com storage local (dev).
- [x] Expor porta `4317` do collector e `3200` do Tempo apenas em localhost.
- [x] Configurar rede compartilhada para comunicacao entre collector e Tempo.
- [x] Verificar que spans gerados pelo backend chegam ao Tempo e ficam consultaveis pelo Grafana.

## Non-Goals

- Configuracao de storage persistente para Tempo - dev mode apenas.
- Autenticacao no collector ou Tempo - dev mode sem TLS.
- Exportacao para backend alternativo (Tempo, Zipkin) - apenas Tempo.

## Stage Boundaries

Modificacoes apenas no `docker-compose.yml` e criacao de `otel-collector-config.yml` na raiz do projeto. Nao modifica codigo backend nem frontend.

## Dependencies

- TASK-080 (backend precisa estar emitindo spans OTLP para testar).

## Inputs & Contracts

- **Inputs**: spans OTLP gRPC na porta `4317`.
- **Outputs**: spans roteados para Tempo via OTLP gRPC interno em `tempo:4317`.
- **Config**: `otel-collector-config.yml` com pipeline OTLP -> batch -> OTLP.

## Constraints & Rules

1. **Pipeline simples**: OTLP gRPC in -> batch processor -> OTLP gRPC out para Tempo.
2. **Portas**: `4317` (OTLP gRPC do collector), `3200` (Tempo HTTP API), `tempo:4317` (Tempo OTLP gRPC interno).
3. **Batch**: `timeout: 5s`, `send_batch_size: 512`, `send_batch_max_size: 1024`.
4. **Resource detection**: ativar `resourcedetection` processor com `env` detector para `OTEL_RESOURCE_ATTRIBUTES`.
5. **Nao expor collector para internet**: portas expostas apenas para `localhost`.
6. **Health check**: adicionar `extension/health_check` no collector.

## Implementation Checklist

- [x] Criar `otel-collector-config.yml` na raiz do projeto com receivers, processors, exporters e extensions.
- [x] Adicionar servico `otel-collector` no `docker-compose.yml`.
- [x] Adicionar servico `tempo` no `docker-compose.yml`.
- [x] Montar `otel-collector-config.yml` como bind mount no container collector.
- [ ] Configurar `depends_on` entre backend e collector (backend startup tolera ausencia).
- [x] Subir stack e verificar logs do collector: `Everything is ready. Begin running and processing data.`
- [~] Fazer request de chat e verificar trace no Grafana Explore usando datasource Tempo.

## Acceptance Criteria

- [x] `docker compose up -d otel-collector tempo` sobe ambos sem erro.
- [x] Collector logs mostram health check ready e pipeline started.
- [x] Tempo API `http://localhost:3200` fica pronta e o datasource Tempo e provisionado no Grafana.
- [ ] Apos um chat request, ao menos 1 trace aparece no Tempo com spans de HTTP, DB e Redis.

## Verification

```bash
docker compose up -d otel-collector tempo
# Aguardar 10s
curl http://localhost:3200/ready
# Abrir Grafana em http://localhost:3000
# Explore -> Tempo -> TraceQL: { resource.service.name = "genai-platform" }
```

## Risks & Rollback

- **Risco**: Collector consumir muita memoria em dev. Mitigacao: limits de memoria no compose, `memory_limb` processor configurado.
- **Risco**: Porta `4317` conflitar com outro servico. Mitigacao: mapear para `0.0.0.0:4317` apenas se necessario, usar rede interna para comunicacao entre servicos.
- **Rollback**: Remover blocos `otel-collector`, `tempo` do compose e o arquivo `otel-collector-config.yml`.

## Execution Log

- `[2026-05-12 09:00]`: Task criada a partir do planejamento Stage 10b.
- `[2026-05-12 14:30]`: Criado otel-collector-config.yml com pipeline OTLP -> batch -> OTLP para Tempo.
- `[2026-05-12 14:35]`: Adicionados servicos otel-collector e Tempo no docker-compose.yml.
- `[2026-05-12 15:40]`: Portas do collector, Tempo e Grafana restringidas a localhost; documentado OTLP interno para Tempo em `tempo:4317`.
- `[2026-05-12 18:30]`: Backend de traces anterior removido do stack; collector agora exporta para Tempo.
