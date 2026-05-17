# Task: TASK-082 - Manual Tracing in Engine (Executor, LLM Node, Handoff)

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-082 |
| **Group** | OBSERVABILITY |
| **Status** | IN_PROGRESS |
| **Stage Ref** | `docs/stages/stage_10b_otel_observability.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | MEDIUM |
| **Owner** | Unassigned |
| **Created At** | 2026-05-12 |
| **Updated At** | 2026-05-12 |

## Context

A auto-instrumentacao (TASK-080) cobre spans de infraestrutura (HTTP request, DB query, Redis command) mas nao captura a semantica de dominio do motor de agentes. Esta task adiciona spans manuais nos pontos criticos do engine: execucao do grafo LangGraph, chamada ao LLM, execucao de ferramentas e resolucao de handoff. Isso permite correlacionar traces de infra com a logica de negocios do agente.

## Objectives

- [x] Criar tracer nomeado `genai.engine` em `backend/app/otel.py` (ou arquivo separado `backend/engine/tracer.py`) para spans de dominio.
- [x] Adicionar span `graph.run` em `engine/executor.py` no metodo `start_stream()` - encapsula toda a execucao de um grafo.
- [x] Adicionar span `llm.call` em `engine/base_graph.py` no node `llm_node` - captura model_name, token count (prompt + completion), temperature.
- [x] Adicionar span `tool.execute` em `engine/tool_executor.py` ou equivalente - captura tool_name e success/failure.
- [x] Adicionar span `handoff.resolve` em `engine/handoff.py` - captura target_instance_id.
- [x] Adicionar span `rag.retrieve` em `engine/rag.py` ou integracao RAG - captura collection, chunk_count, score.
- [x] Propagar `trace_id` do OTel para o run trace custom (TASK-077) como campo `otel_trace_id`.
- [ ] Garantir que `_redact()` e aplicado em qualquer span attribute que contenha texto de prompt ou resposta.

## Non-Goals

- Instrumentacao de cada no individual do LangGraph (graph nao expoe hooks finos).
- Cobertura de canais (webhook, telegram, etc.) - limitado ao engine core.
- Cobertura do consumer de indexacao RAG gerenciado pelo backend.

## Stage Boundaries

Modificacoes em `backend/app/otel.py`, `backend/engine/executor.py`, `backend/engine/base_graph.py` e arquivos relacionados de tools, handoff, RAG. Nao modifica infraestrutura nem frontend.

## Dependencies

- TASK-080 (SDK OTel precisa estar disponivel).
- Stage 06 (RAG) - se `rag.retrieve` span for implementado.

## Inputs & Contracts

- **Inputs**: tracer `genai.engine` obtido via `opentelemetry.trace.get_tracer()`.
- **Outputs**: spans com atributos semanticos de dominio.
- **Span attributes**: `instance_id`, `tenant_id`, `model_name`, `prompt_tokens`, `completion_tokens`, `temperature`, `tool_name`, `tool_duration_ms`, `handoff_target`, `rag_collection`, `rag_chunk_count`, `error` (se houver).

## Constraints & Rules

1. **Nao quebrar fluxo existente**: spans sao adicionados com `tracer.start_as_current_span()` em blocos `with` - zero impacto na logica de negocios.
2. **Sanitizacao**: nenhum span attribute pode conter prompt do usuario, resposta do LLM, api keys ou tokens de autenticacao.
3. **Performance**: spans devem ter `set_attribute` apenas com dados ja disponiveis - sem queries extras.
4. **Record exception**: capturar excecoes com `span.record_exception()` e `span.set_status(Status(StatusCode.ERROR))`.
5. **Atributos semanticos**: usar naming conventions OTel quando existir (`gen_ai.request.model`, `gen_ai.response.completions`, `db.system`).

## Implementation Checklist

- [x] Criar `backend/engine/tracer.py` com `get_tracer("genai.engine")` reexportando o tracer global.
- [x] Em `executor.py:start_stream()`: adicionar span `graph.run` com atributos `instance_id`, `tenant_id`, `model`.
- [x] Em `base_graph.py:llm_node`: adicionar span `llm.call` com modelo, tokens e `temperature`.
- [x] Em tool executor: adicionar span `tool.execute` com `tool_name` e `success`.
- [x] Em handoff resolver: adicionar span `handoff.resolve` com `target_instance_id`.
- [x] Em RAG retriever: adicionar span `rag.retrieve` com `chunk_count` e `max_score`.
- [x] Propagar `otel_trace_id` para o run trace JSON persistido em `agent_run_traces.trace`.
- [ ] Verificar que os spans aparecem aninhados corretamente no Grafana Explore via Tempo.

## Acceptance Criteria

- [ ] Cada execucao de chat gera um span `graph.run` como parent dos spans internos.
- [ ] Spans `llm.call` aparecem com `model_name`, `prompt_tokens`, `completion_tokens` preenchidos.
- [ ] Spans `tool.execute` aparecem com `tool_name` e `success`.
- [ ] Spans `handoff.resolve` aparecem com `target_instance_id`.
- [ ] Spans `rag.retrieve` aparecem com `collection_name` e `chunk_count`.
- [ ] Nenhum span attribute contem texto de prompt, resposta ou api key.
- [ ] Trace ID do OTel aparece no registro `agent_run_traces.trace->otel_trace_id`.

## Verification

```bash
# Executar chat e verificar spans no Grafana Explore via Tempo
docker compose up -d
# Fazer request de chat
curl -X POST http://localhost:8000/agent/instances/{id}/chat ...
# Abrir Grafana http://localhost:3000
# Explore -> Tempo -> buscar trace; deve mostrar arvore: graph.run > llm.call, tool.execute, rag.retrieve, handoff.resolve
```

## Risks & Rollback

- **Risco**: Span mal fechado (excecao nao tratada) travar o flow do executor. Mitigacao: uso consistente de `with tracer.start_as_current_span()` que garante fechamento.
- **Risco**: Sobre-carga de spans (centenas de tools por run). Mitigacao: amostragem via `Sampler` ou config `OTEL_TRACES_SAMPLER`.
- **Rollback**: Reverter as adicoes de span nos arquivos `executor.py`, `base_graph.py`, `tracer.py` e tool/handoff/rag executors.

## Execution Log

- `[2026-05-12 09:00]`: Task criada a partir do planejamento Stage 10b.
- `[2026-05-12 14:50]`: Criado engine/tracer.py com tracer nomeado "genai.engine".
- `[2026-05-12 14:55]`: Adicionado span graph.run em executor.py:start_stream().
- `[2026-05-12 15:00]`: Adicionado span llm.call em base_graph.py:llm_node() com model_name, temperature, tokens.
- `[2026-05-12 15:05]`: Adicionado span tool.execute em base_graph.py:dispatch_node().
- `[2026-05-12 15:10]`: Adicionado span handoff.resolve em base_graph.py:handoff_node().
- `[2026-05-12 15:15]`: Adicionado span rag.retrieve em nodes/rag_node.py.
- `[2026-05-12 15:45]`: Corrigidos atributos setados apos fechamento de span; `otel_trace_id` agora e gravado no trace JSON persistido.
