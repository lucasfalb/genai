# Stage 07 Tasks - Hand-off, Routing e Transfer Logic

| ID | Task | Status | Priority | Depends On |
| :--- | :--- | :--- | :--- | :--- |
| TASK-048 | [agent_links Migration e Repositorio](task_048_agent_links_migration_repository.md) | PENDING | CRITICAL | TASK-003 |
| TASK-049 | [agent_links CRUD API Tenant-Scoped](task_049_agent_links_crud_api.md) | PENDING | HIGH | TASK-048, TASK-030 |
| TASK-050 | [Tool Fantasma no Bootstrap e AgentState](task_050_ghost_tool_bootstrap_agent_state.md) | PENDING | CRITICAL | TASK-048, TASK-019 |
| TASK-051 | [handoff_node, HandoffSummarizer e HandoffSanitizer](task_051_handoff_node_summarizer_sanitizer.md) | PENDING | CRITICAL | TASK-050, TASK-039 |
| TASK-052 | [Router Classifier IntentRouter](task_052_router_classifier_intent_router.md) | PENDING | HIGH | TASK-050 |
| TASK-053 | [Verificacao Stage 07 Handoff](task_053_stage_07_handoff_verification.md) | PENDING | HIGH | TASK-049, TASK-051, TASK-052 |

## Scope

Estas tasks cobrem o Stage 07 definido em `docs/stages/stage_07_handoff.md`: tabela `agent_links`, CRUD de vinculos entre instancias, tool fantasma no bootstrap, `handoff_node` com sanitizacao e resumo de contexto, e router classifier proativo.

## Implementation Order

1. Migration e repositorio de `agent_links`.
2. CRUD de vinculos tenant-scoped.
3. Tool fantasma no bootstrap e estado do agente.
4. handoff_node com HandoffSummarizer e HandoffSanitizer.
5. Router classifier para transfer_mode = router_classifier.
6. Verificacao end-to-end.

## Notes

- Agente destino nao recebe historico bruto — apenas resumo sanitizado e ultimas N mensagens.
- `transfer_mode = llm_decision` e o modo padrao; `router_classifier` e opcional.
- Toda rota nova deve ganhar request Bruno em `genai-endpoints/`.
- Toda rota JSON usa envelope `ApiResponse[T]`.
