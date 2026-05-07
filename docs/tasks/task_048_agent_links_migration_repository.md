# Task: TASK-048 - agent_links Migration e Repositorio

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-048 |
| **Group** | HANDOFF |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_07_handoff.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Hand-off entre agentes requer uma tabela que mapeia qual instancia pode transferir para qual outra, com nome da tool fantasma e descricao de quando transferir. Esta task cria a migration e o repositorio.

## Objectives

- [ ] Criar migration Alembic para tabela `agent_links` com UNIQUE(source_instance_id, target_instance_id).
- [ ] Implementar `AgentLinkRepository` em `database/repositories/agent_links.py`.
- [ ] Operacoes: create, list_by_source, get, enable/disable, delete.
- [ ] Testar: create link, list por source, unicidade de par source/target.

## Non-Goals

- Endpoints REST (TASK-049).
- Tool fantasma no bootstrap (TASK-050).

## Stage Boundaries

Apenas banco de dados. Nenhum endpoint ou engine nesta task.

## Dependencies

- TASK-003 (tenant-scoped schema — padrao RLS)

## Inputs & Contracts

- **Inputs**: `tenant_id`, `source_instance_id`, `target_instance_id`, `transfer_tool_name`, `trigger_description`, `transfer_mode`.
- **Outputs**: registros em `agent_links`.
- **Schemas**: ver DDL em `docs/stages/stage_07_handoff.md`.

## Constraints & Rules

1. UNIQUE constraint em `(source_instance_id, target_instance_id)`.
2. `transfer_mode`: `llm_decision | router_classifier`.
3. Sem RLS proprio — isolamento via FK para `agent_instances.tenant_id`.
4. `is_enabled = true` por default.

## Implementation Checklist

- [ ] Criar migration `alembic/versions/XXXX_add_agent_links.py`.
- [ ] Criar `database/repositories/agent_links.py` com `AgentLinkRecord` e `AgentLinkRepository`.
- [ ] Testar: create, list_by_source, unicidade (segundo insert com mesmo par levanta erro).

## Acceptance Criteria

- [ ] Migration cria `agent_links` com constraints corretas.
- [ ] Segundo link com mesmo par source/target levanta erro de unicidade.
- [ ] `list_by_source` retorna apenas links da instancia passada.

## Verification

```bash
cd backend
alembic upgrade head
pytest tests/test_stage_07_repositories.py
```

## Risks & Rollback

- **Rollback**: `alembic downgrade -1`.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para migration e repositorio de agent_links.
