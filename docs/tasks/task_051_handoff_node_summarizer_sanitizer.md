# Task: TASK-051 - handoff_node, HandoffSummarizer e HandoffSanitizer

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-051 |
| **Group** | HANDOFF |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_07_handoff.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Quando o LLM chama uma tool fantasma de hand-off, o `handoff_node` interrompe a execucao do agente de origem, sanitiza o historico, gera um resumo objetivo e inicia o agente de destino com contexto seguro.

## Objectives

- [ ] Implementar `handoff_node` em `engine/nodes/handoff_node.py`.
- [ ] Implementar `HandoffSanitizer.keep_recent_conversation(messages, max_messages=8)` em `engine/handoff.py`.
- [ ] Implementar `HandoffSummarizer` que usa LLM para gerar `HandoffSummary`.
- [ ] Definir `HandoffSummary(source_instance_id, target_instance_id, reason, user_goal, known_facts, open_questions, actions_already_taken, safety_notes)`.
- [ ] `handoff_node` resolve link, prepara estado sanitizado, executa agente destino e retorna `final_response`.
- [ ] Testar: link valido executa agente destino, link invalido retorna erro controlado.

## Non-Goals

- Router classifier (TASK-052).
- Armazenamento de historico de hand-offs para analytics.

## Stage Boundaries

Apenas logica de hand-off. Nenhum endpoint novo.

## Dependencies

- TASK-050 (tool fantasma — bootstrap popula `linked_agents`)
- TASK-039 (llm_node real — agente destino usa o mesmo grafo)

## Inputs & Contracts

- **Inputs**: `AgentState.pending_tool_calls[0]` com `name = transfer_tool_name` e `args.reason`.
- **Outputs**: `AgentState.final_response` (do agente destino) + `AgentState.handoff_target`.
- **Schemas**: `HandoffSummary` Pydantic model.

## Constraints & Rules

1. Agente destino recebe apenas mensagens de role `user/assistant/human/ai` sem `tool_calls`.
2. Maximo de 8 mensagens recentes passadas ao agente destino.
3. `HandoffSummarizer` usa LLM para gerar resumo — deve ter timeout configuravel.
4. Link nao encontrado retorna `tool_results = [{error: "Agente X nao disponivel"}]`.
5. Sem vazamento de `tool_calls` internas, schemas ou `system_prompt` do agente de origem.

## Implementation Checklist

- [ ] Criar `engine/handoff.py` com `HandoffSummary`, `HandoffSanitizer` e `HandoffSummarizer`.
- [ ] Criar `engine/nodes/handoff_node.py`.
- [ ] Integrar `handoff_node` no `base_graph` (ja registrado como no-op).
- [ ] Testar: hand-off com link valido, link invalido, sanitizacao remove tool_calls.

## Acceptance Criteria

- [ ] `handoff_node` com link valido retorna `final_response` do agente destino.
- [ ] Link invalido retorna estado com `tool_results` de erro sem crash.
- [ ] `HandoffSanitizer` remove mensagens de tool_call do historico.
- [ ] `HandoffSummary` preenchido com `reason` da tool call.

## Verification

```bash
cd backend
pytest tests/test_stage_07_handoff_node.py
```

## Risks & Rollback

- **Risks**: loop infinito se agente destino tambem fizer hand-off de volta.
- **Rollback**: substituir `handoff_node` por no-op que retorna erro controlado.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para handoff_node e contratos de transferencia.
