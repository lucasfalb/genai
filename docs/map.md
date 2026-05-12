# Mapa Mestre de Implementação

_Fonte canônica: [`platform_technical_spec.md`](platform_technical_spec.md). A especificação completa agora vive em /docs como referência final._

## Como Navegar

- [`architecture_overview.md`](architecture_overview.md): visão macro da plataforma, fluxo de dados, segurança, frontend, infraestrutura e observabilidade.
- [`stages/stage_01_core_db.md`](stages/stage_01_core_db.md): PostgreSQL, RLS, multi-tenancy e schema base.
- [`stages/stage_02_auth_rbac.md`](stages/stage_02_auth_rbac.md): autenticação, JWT, roles e permissões.
- [`stages/stage_03_registry.md`](stages/stage_03_registry.md): registry de skills/tools, credenciais, Vault e cache de metadata.
- [`stages/stage_04_engine.md`](stages/stage_04_engine.md): LangGraph, AgentState, RunBootstrap, grafo base e Redis Lock.
- [`stages/stage_05_base_multitenant_workflows.md`](stages/stage_05_base_multitenant_workflows.md): workflows base multi-tenant, auth lifecycle, convites, members, tenants, instancias e auditoria.
- [`stages/stage_05_prompts.md`](stages/stage_05_prompts.md): Prompt Sandwich, cache do prompt composto, sanitization e injection.
- [`stages/stage_06_rag.md`](stages/stage_06_rag.md): Qdrant, embeddings, documentos, status de indexação e retrieval.
- [`stages/stage_07_handoff.md`](stages/stage_07_handoff.md): hand-off multiagente, router classifier e resumo sanitizado.
- [`stages/stage_08_channels.md`](stages/stage_08_channels.md): API, Widget, Webhooks, WhatsApp e Outbound Data Bridge.
- [`stages/stage_09_frontend.md`](stages/stage_09_frontend.md): frontend SvelteKit 5 completo conectado aos 59 endpoints da API REST.
- [`tasks/task_template.md`](tasks/task_template.md): template base para quebrar stages em tasks executáveis.

## Dependências Entre Stages

```text
01 Core DB
   ↓
02 Auth/RBAC ──→ 03 Registry
   ↓              ↓
04 Execution Engine ← 05 Prompt Runtime
   ↓
06 RAG ──→ 07 Hand-off
   ↓        ↓
08 Channels + Outbound Sync
```

## 14. Roadmap de Implementação

### Fase 1 — Fundação (semanas 1-3)

- [ ] Monorepo, Docker Compose, CI/CD básico
- [ ] Schema PostgreSQL + migrations (Alembic)
- [ ] Auth: registro, login, JWT, verificação de email
- [ ] RBAC middleware
- [ ] Multi-tenancy: `tenant_id` obrigatório + RLS
- [ ] CRUD de tenants e users (superadmin)
- [ ] Frontend: login, registro, página awaiting, routing por role

### Fase 2 — Agente Base e Prompt Dinâmico (semanas 4-6)

- [ ] Catálogo de skills e tools (superadmin)
- [ ] CRUD de instâncias por tenant
- [ ] Ativação de skills e tools por instância
- [ ] Cache Redis de prompt composto, metadata de tools/skills e credenciais decriptadas com TTL curto
- [ ] Invalidação do cache de prompt/metadata em saves administrativos no dashboard
- [ ] `PromptBuilder`: montagem do prompt sanduíche em runtime
- [ ] `PromptSanitizer`: limite de tokens, densidade de instruções, conflitos entre blocos e nomes únicos de tools
- [ ] Validação de output por canal/schema antes de persistir resposta final
- [ ] `AgentState` e `RunBootstrap`
- [ ] Grafo LangGraph base (rag → llm → dispatch)
- [ ] Lock distribuído por `session_id` para serializar escritas do checkpointer
- [ ] Streaming SSE end-to-end
- [ ] Playground básico no frontend

### Fase 3 — Hand-off entre Agentes (semanas 7-8)

- [ ] Tabela `agent_links` e API de configuração
- [ ] Tools fantasma geradas dinamicamente por instância
- [ ] `handoff_node`: interrupção e transferência com Resumo de Hand-off sanitizado
- [ ] `IntentRouter`: classifier para modo proativo
- [ ] UI de configuração de vínculos no dashboard
- [ ] Testes de hand-off end-to-end

### Fase 4 — RAG e Knowledge Base (semanas 9-11)

- [ ] Pipeline de indexação de documentos (PDF, DOCX, URL)
- [ ] Status de indexação por documento e coleção (`empty`, `indexing`, `ready`, `partial`, `failed`)
- [ ] UI de progresso/alerta de Indexing na Knowledge Base, aba RAG e Playground
- [ ] Integração Qdrant com filtros por tenant e collection
- [ ] `TenantRetriever` com RBAC
- [ ] UI de gestão de coleções e documentos
- [ ] Configuração de RAG scope por instância

### Fase 5 — Canais e Widget (semanas 12-13)

- [ ] Geração de API keys por canal
- [ ] Widget JavaScript embeddável
- [ ] Validação de domínio para widget
- [ ] Webhook receiver
- [ ] Canal WhatsApp via webhook/provider adapter
- [ ] UI de configuração de canais
- [ ] `outbound_sync_config` em Advanced Settings dos canais
- [ ] Outbound Data Bridge com Redis broker, worker RQ/Celery e retries com exponential backoff
- [ ] Mapping dinâmico com templates e dead-letter/replay no dashboard

### Fase 6 — Observabilidade e Analytics (semanas 14-16)

- [x] Traces por execução (skills, tools, hand-offs, RAG) — Stage 10 (TASK-077 a 079)
- [ ] Métricas Prometheus + Grafana — Stage 10c (futuro)
- [ ] Dashboard de analytics por tenant — Stage 10c (futuro)
- [ ] Logs estruturados com redaction de dados sensíveis — Stage 10c (futuro)

### Stage 11 - OpenTelemetry & Tempo Tracing

Stage de tracing distribuido com OpenTelemetry. Ver `docs/stages/stage_10b_otel_observability.md`.

| ID | Task | Status |
| :--- | :--- | :--- |
| TASK-080 | [OTel SDK Bootstrap](docs/tasks/task_080_otel_sdk_bootstrap.md) | IN_PROGRESS |
| TASK-081 | [OTel Collector + Tempo](docs/tasks/task_081_otel_collector_tempo.md) | IN_PROGRESS |
| TASK-082 | [Manual Tracing in Engine](docs/tasks/task_082_manual_tracing_engine.md) | IN_PROGRESS |
| TASK-083 | [Grafana Dashboards & E2E](docs/tasks/task_083_grafana_dashboards.md) | IN_PROGRESS |

### Fase 7 — Polish e Enterprise (semanas 17-20)

- [ ] SSO (SAML, OAuth)
- [ ] Billing e limites de plano
- [ ] Rate limiting avançado
- [ ] Exportação de analytics
- [ ] Disaster recovery e backups automáticos
- [ ] Integrações de knowledge (Notion, Confluence, S3)
