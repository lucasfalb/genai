# Task: TASK-078 - Frontend Debug Panel (Run Trace Inspector)

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-078 |
| **Group** | OBSERVABILITY |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_10_observability.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Codex |
| **Created At** | 2026-05-10 |
| **Updated At** | 2026-05-10 |

## Context

Com TASK-077 expondo trace via SSE + REST, o tenant precisa de uma superficie visual para inspecionar prompt montado, chunks RAG, tool calls e hand-offs apos cada execucao. Esta task entrega a aba "Debug" no detalhe da instancia consumindo esses contratos.

## Objectives

- [x] Adicionar tipos `RunTracePayload`, `RunTraceResponse`, `RunTraceListItem`, `RunTraceSection`, `RunTraceChunk`, `RunTraceToolCall`, `RunTraceToolResult` em `lib/api/types.ts`.
- [x] Estender `lib/api/chat.ts` com callback `onTrace` no `streamChat` e helper `tracesApi` (`getLatest`, `get`, `list`).
- [x] Persistir `run_id` corrente em `chatSession.setLastRunId/getLastRunId` via sessionStorage.
- [x] Criar componente `lib/components/instance/run-trace-panel.svelte` com colapsaveis: stats, system prompt (camadas), RAG chunks, tools/skills, hand-off, raw JSON, runs recentes.
- [x] Criar rota `/app/{tenant}/instances/{id}/debug/+page.svelte` montando o painel.
- [x] Adicionar tab "Debug" em `+layout.svelte`.
- [x] Implementar dashboard tenant-level em `/app/{tenant}/observability` com consumo de tokens por run e por agente.

## Non-Goals

- Streaming live de trace durante execucao (consumido via REST apos `run.trace` ou via fallback `getLatest`).
- Edicao de prompt no Debug — read-only.
- Exportacao de trace (CSV/JSON download) — feature futura.

## Stage Boundaries

Frontend-only. Reutiliza endpoints e SSE da TASK-077.

## Dependencies

- TASK-074 (chat panel + streamChat)
- TASK-077 (backend trace endpoints + SSE event)

## Inputs & Contracts

- **Tipos**: vide `lib/api/types.ts` `RunTrace*`.
- **API**:
  - `tracesApi.getLatest(instanceId, sessionId?)` -> `RunTraceResponse`
  - `tracesApi.get(instanceId, runId)` -> `RunTraceResponse`
  - `tracesApi.list(instanceId, sessionId?, limit?)` -> `RunTraceListItem[]`
  - `tracesApi.listTenant(limit?)` -> `RunTraceListItem[]`
- **SessionStorage**:
  - `chat_session_<instanceId>` (existente)
  - `chat_last_run_<instanceId>` (novo) — persiste `run_id` do ultimo run.
- **Component props**: `RunTracePanel { instanceId: string }`.
- **Route**: `/app/{tenant}/instances/{id}/debug` — herda `data` do `+layout.server.ts` parent (tem `data.instance.id`).

## Constraints & Rules

1. Painel busca trace ao mount: prioriza `chatSession.getLastRunId(instanceId)` -> fallback `getLatest(instanceId, sessionId)`.
2. Botao "Atualizar" re-fetch.
3. Lista de runs recentes (`history`) clicavel — troca trace exibido sem recarregar pagina.
4. Erro 404 vira mensagem amigavel ("Nenhum run encontrado").
5. `run.trace` event no chat: handler `onTrace` salva `run_id` em sessionStorage para o Debug panel pegar fresh.
6. Stage 07 stubs (tools dispatch + handoff) sao explicitamente sinalizados na UI ("Stage 07 ainda pendente").

## Implementation Checklist

- [x] `lib/api/types.ts` types.
- [x] `lib/api/chat.ts` `onTrace` callback + dispatcher case `run.trace`.
- [x] `lib/api/chat.ts` `tracesApi` (3 metodos).
- [x] `lib/api/chat.ts` `chatSession.setLastRunId/getLastRunId` + `clear()` limpa run_id tambem.
- [x] `lib/components/instance/test-agent-chat.svelte` chama `setLastRunId` em `onTrace`/`onCompleted`.
- [x] `lib/components/instance/run-trace-panel.svelte` componente completo (stats, prompt layers, RAG, tools, handoff, raw JSON, history).
- [x] Route `/instances/[id]/debug/+page.svelte`.
- [x] `+layout.svelte` tabs array com entrada "Debug".
- [x] Route `/observability/+page.svelte` com KPIs de tokens, tabela de runs e ranking por agente.

## Acceptance Criteria

- [x] Aba "Debug" aparece nos tabs do detalhe da instancia.
- [x] Acessar `/debug` apos enviar uma mensagem renderiza trace com prompt em camadas, chunks RAG (se houver), tools/skills, hand-off (se houver).
- [x] "Atualizar" re-fetch sem reload de pagina.
- [x] Lista de runs recentes carrega via `tracesApi.list` e troca trace ao clicar.
- [x] Observability mostra total, media e split prompt/completion/embedding dos ultimos run traces do tenant.
- [x] Sem trace: estado vazio com instrucao para enviar mensagem.
- [x] `npm run check` zero erros nos arquivos novos.

## Verification

```bash
cd frontend
npm run check
# manual: enviar mensagem em /app/{tenant}/instances/{id}, abrir aba Debug, conferir prompt camadas, RAG chunks, runs recentes.
```

## Risks & Rollback

- **Risco**: trace muito grande causa lag ao expandir "Raw JSON". Mitigacao: section colapsada por default.
- **Risco**: `RunTracePanel` falha em runs antigos sem `system_prompt_sections` populado. Mitigacao: defaults vazios + verificacoes nullables.
- **Rollback**: remover rota `debug/`, componente, entrada da tab e helpers — backend sobrevive.

## Execution Log

- `[2026-05-10 02:45]`: Task criada como parte do Stage 10.
- `[2026-05-10 02:50]`: Tipos `RunTrace*` adicionados em `lib/api/types.ts`.
- `[2026-05-10 02:55]`: `chat.ts` ganha `onTrace` callback, `tracesApi` (3 metodos), `chatSession.setLastRunId/getLastRunId`.
- `[2026-05-10 03:00]`: `test-agent-chat.svelte` salva `run_id` em sessionStorage via `onTrace`/`onCompleted`.
- `[2026-05-10 03:10]`: `run-trace-panel.svelte` criado com 6 secoes colapsaveis + lista de runs recentes.
- `[2026-05-10 03:15]`: Rota `/instances/[id]/debug/+page.svelte` criada montando `<RunTracePanel />`.
- `[2026-05-10 03:18]`: Tab "Debug" adicionada em `+layout.svelte`.
- `[2026-05-10 03:20]`: `npm run check` -> zero erros nos arquivos novos. Status -> COMPLETED.
- `[2026-05-11 04:30]`: Reescrita premium: integracao com `@xyflow/svelte`, grafo de execucao (User -> RAG -> LLM -> Tools/Handoff/Respond) com nos colorizados por estado, reactive auto-load via `chatSessionStore` (Svelte 5 runes), 6 stats cards no topo, secoes com hover, miniMap, controles, badge "live" quando session ativa, fallback amigavel quando nao ha trace, mensagem clara quando RAG retorna 0 chunks (sem hits vs scope vazio). Compatibilidade com TASK-079 (Constraints): grafo continua mostrando System Prompt em camadas (core/instructions/tools/guardrails/constraints).
- `[2026-05-12 19:30]`: `/observability` substituido por dashboard de consumo de tokens usando `tracesApi.listTenant()` e nomes de agentes de `instancesApi.list()`.
