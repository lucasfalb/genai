# Task: TASK-083 - Grafana Dashboards & End-to-End Verification

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-083 |
| **Group** | OBSERVABILITY |
| **Status** | IN_PROGRESS |
| **Stage Ref** | `docs/stages/stage_10b_otel_observability.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | MEDIUM |
| **Owner** | Unassigned |
| **Created At** | 2026-05-12 |
| **Updated At** | 2026-05-12 |

## Context

Com OTel SDK instrumentado (TASK-080), collector + Tempo rodando (TASK-081) e spans de dominio no engine (TASK-082), a etapa final e unificar a visualizacao no Grafana: adicionar servico Grafana no docker-compose, configurar datasource Tempo, criar dashboard de traces por endpoint e executar verificacao end-to-end completa do pipeline de tracing.

## Objectives

- [x] Adicionar servico `grafana` no `docker-compose.yml` com imagem `grafana/grafana:11.5.2`.
- [x] Configurar provisioning do datasource Tempo no Grafana via `datasources.yml` automatico.
- [x] Criar dashboard "GenAI Workflow Telemetry" com search de traces por servico, erros, spans de dominio, workflows funcionais e paineis para todos os endpoints FastAPI registrados.
- [ ] Configurar volumes persistentes para Grafana (opcional em dev).
- [~] Verificar end-to-end: backend -> collector -> Tempo -> Grafana.
- [x] Documentar o fluxo completo em `docs/operations/otel_tracing.md`.

## Non-Goals

- Dashboards de metricas Prometheus (fora de escopo do Stage 10b).
- Alertas ou notificacoes.
- Autenticacao Grafana avancada (admin/admin default).
- Importacao de dashboards de terceiros.

## Stage Boundaries

Modificacoes no `docker-compose.yml`, criacao de `grafana/datasources/datasources.yml` e `grafana/dashboards/agent-traces.json`. Criacao de `docs/operations/otel_tracing.md`.

## Dependencies

- TASK-080 (SDK emitindo spans).
- TASK-081 (collector + Tempo rodando).
- TASK-082 (spans de dominio visiveis).

## Inputs & Contracts

- **Inputs**: Tempo OTLP gRPC endpoint `tempo:4317` (ja existente do TASK-081).
- **Outputs**: Grafana UI em `http://localhost:3000` com datasource Tempo configurado.
- **Config**: `grafana/datasources/datasources.yml` com tipo `tempo`, URL `http://tempo:3200`.

## Constraints & Rules

1. **Provisionamento**: datasource e dashboards devem ser provisionados automaticamente (via `grafana/datasources/` e `grafana/dashboards/`), sem configuracao manual na UI.
2. **Porta**: Grafana exposto em `3000` (default), mapeado para `0.0.0.0:3000`.
3. **Dashboard JSON**: deve ser versionado no repo (arquivo `.json` em `grafana/dashboards/`) e conter paineis TraceQL para cada operacao FastAPI registrada.
4. **Login dev**: `admin` / `admin`.
5. **Documentacao**: `docs/operations/otel_tracing.md` deve conter passo-a-passo para validar o pipeline completo.

## Implementation Checklist

- [x] Adicionar servico `grafana` no `docker-compose.yml` com volumes para datasources e dashboards.
- [x] Criar `grafana/datasources/datasources.yml` com datasource Tempo.
- [x] Criar `grafana/dashboards/agent-traces.json` com dashboard completo de endpoint telemetry.
- [x] Criar diretorio `grafana/dashboards/` no projeto.
- [x] Configurar `GF_INSTALL_PLUGINS` se necessario (nenhum no dev).
- [x] Subir stack completa: `docker compose up -d`.
- [x] Verificar Grafana UI: `http://localhost:3000` -> datasource Tempo provisionado.
- [ ] Executar chat e confirmar trace visivel no Grafana Explore.
- [x] Criar `docs/operations/otel_tracing.md` com guia de uso e verificacao.

## Acceptance Criteria

- [x] Grafana inicia sem erros com datasource Tempo configurado automaticamente.
- [x] Em "Explore" -> datasource Tempo, e possivel buscar traces por `service.name = "genai-platform"`.
- [ ] Apos chat request, o trace completo (HTTP -> graph.run -> llm.call -> tool.execute) aparece na visualizacao.
- [x] Dashboard "GenAI Workflow Telemetry" mostra dados dos ultimos traces HTTP, agrupa endpoints por fluxo funcional e possui painel dedicado para cada endpoint FastAPI registrado.
- [x] `docs/operations/otel_tracing.md` documenta o fluxo completo.

## Verification

```bash
docker compose up -d
# Aguardar 15s
# Abrir http://localhost:3000 (acesso anonimo; admin/admin se login for exigido)
# Ir em Connections -> Data Sources -> Tempo -> "Save & Test" -> deve mostrar "Success"
# Ir em Explore -> selecionar Tempo -> buscar servico "genai-platform" -> "Run query"
# Abrir Dashboards -> GenAI Workflow Telemetry
# Executar chat via curl e verificar novo trace aparece no Grafana
```

## Risks & Rollback

- **Risco**: Dashboard JSON complexo demais. Mitigacao: comecar com JSON minimalista de 1 painel (trace search) e evoluir.
- **Risco**: Conflito de porta 3000 com outro servico. Mitigacao: mapear para porta alternativa via env var.
- **Rollback**: Remover bloco `grafana` do compose e diretorio `grafana/`.

## Execution Log

- `[2026-05-12 09:00]`: Task criada a partir do planejamento Stage 10b.
- `[2026-05-12 15:50]`: Adicionado provisioning do Grafana, datasource Tempo com UID estavel e dashboard inicial de trace search.
- `[2026-05-12 18:00]`: Validado via API Grafana: datasource `Tempo` provisionado e dashboard `Agent Traces` encontrado.
- `[2026-05-12 18:30]`: Datasource Grafana migrado para Tempo.
- `[2026-05-12 18:40]`: Dashboard substituido por `GenAI Endpoint Telemetry`, com 90 paineis de endpoints e 96 paineis totais; validado via API Grafana e TraceQL direto no Tempo.
- `[2026-05-12 18:55]`: Dashboard reorganizado como `GenAI Workflow Telemetry`, com 10 workflows, 90 endpoints cobertos e 126 paineis totais.
