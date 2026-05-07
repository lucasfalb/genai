# Task: TASK-050 - Tool Fantasma no Bootstrap e AgentState

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-050 |
| **Group** | HANDOFF |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_07_handoff.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Para o LLM do agente de origem poder iniciar um hand-off, o agente de destino precisa aparecer como uma tool no prompt e nos `tool_schemas`. Esta task adapta o bootstrap para carregar `linked_agents` e construir os schemas de tools fantasma.

## Objectives

- [ ] Estender `ToolMetadataCache` para incluir `linked_agents` (lista de `AgentLinkRecord` ativos).
- [ ] Implementar `_build_handoff_schema(link)` no bootstrap que gera schema OpenAI function calling com parametro `reason: str`.
- [ ] Incluir schemas de hand-off em `AgentState.tool_schemas`.
- [ ] Incluir lista de `linked_agents` em `AgentState.linked_agents`.
- [ ] Garantir que `route_after_llm` identifica hand-off por `transfer_tool_name` em `linked_agents`.
- [ ] Testar: bootstrap com 0, 1 e N links ativos.

## Non-Goals

- Execucao do hand-off (TASK-051).
- Router classifier (TASK-052).

## Stage Boundaries

Apenas bootstrap e estado. Nenhum endpoint novo.

## Dependencies

- TASK-048 (AgentLinkRepository — fonte dos links)
- TASK-019 (AgentState — campo `linked_agents` ja definido)

## Inputs & Contracts

- **Inputs**: `instance_id`, `tenant_id` no bootstrap.
- **Outputs**: `AgentState.tool_schemas` inclui schemas de hand-off; `AgentState.linked_agents` preenchido.
- **Schemas**: tool schema `{name: transfer_tool_name, description: trigger_description, parameters: {reason: str}}`.

## Constraints & Rules

1. Apenas links com `is_enabled = true` aparecem como tools.
2. `transfer_tool_name` deve ser unico dentre todas as tools/skills/links da instancia.
3. `ToolMetadataCache` invalida quando `agent_links` sao modificados (coberto por TASK-049).

## Implementation Checklist

- [ ] Estender `ToolMetadataCache.get` para consultar `agent_links` ativos e incluir em `ToolMetadata.linked_agents`.
- [ ] Implementar `_build_handoff_schema` em `engine/bootstrap.py`.
- [ ] Adicionar schemas de hand-off a `tool_schemas` no `AgentState`.
- [ ] Atualizar `route_after_llm` para detectar hand-off por `transfer_tool_name`.
- [ ] Testar: bootstrap retorna schemas corretos, routing detecta hand-off.

## Acceptance Criteria

- [ ] Bootstrap com 2 links ativos gera 2 schemas de tool fantasma.
- [ ] `route_after_llm` retorna `handoff` quando LLM chama `transfer_tool_name`.
- [ ] Links desabilitados nao aparecem em `tool_schemas`.

## Verification

```bash
cd backend
pytest tests/test_stage_07_bootstrap_ghost_tools.py
```

## Risks & Rollback

- **Risks**: colisao de nomes de tools se `transfer_tool_name` duplicar skill/tool existente.
- **Rollback**: remover `linked_agents` do `ToolMetadata` e retornar lista vazia.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para tool fantasma no bootstrap.
