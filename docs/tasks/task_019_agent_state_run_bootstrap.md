# Task: TASK-019 - Agent State e Run Bootstrap

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-019 |
| **Group** | ENGINE |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_04_engine.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O runtime precisa montar um estado inicial por execucao com tenant, instancia, sessao, prompt base e capabilities vindas do registry.

## Objectives

- [x] Definir `AgentState`.
- [x] Criar bootstrap de run por `tenant_id`, `instance_id` e `session_id`.
- [x] Carregar metadata de skills/tools ativas pelo `ToolMetadataCache`.
- [x] Carregar linked agents e schemas de handoff.

## Non-Goals

- Executar LLM real.
- Implementar Prompt Runtime completo do Stage 05.

## Stage Boundaries

Esta task prepara o estado do Stage 04 e consome metadata do Stage 03 sem implementar stages posteriores.

## Dependencies

- TASK-015

## Inputs & Contracts

- **Inputs**: tenant context, instance id, session id e channel.
- **Outputs**: `AgentState` validado para executor.
- **Schemas**: modelos internos em `engine/state.py`.

## Constraints & Rules

1. Bootstrap deve validar que a instancia pertence ao tenant ativo.
2. Metadata nao deve carregar segredos.
3. Prompt final completo fica fora desta task.

## Implementation Checklist

- [x] Criar pacote `engine`.
- [x] Criar tipos/modelos de estado.
- [x] Criar `RunBootstrap`.
- [x] Testar instancia inexistente ou fora do tenant.

## Acceptance Criteria

- [x] Bootstrap retorna tenant, instance, session e capabilities ativas.
- [x] Bootstrap rejeita instancia inexistente no tenant.
- [x] Linked agents ficam representados no estado quando houver links.
- [x] Estado nao contem credenciais.

## Verification

```bash
pytest tests/test_stage_04_engine.py
```

## Risks & Rollback

- **Risks**: bootstrap permissivo pode executar agente de outro tenant.
- **Rollback**: bloquear endpoint de chat ate corrigir validacao de instancia.

## Execution Log

- `[2026-05-07 14:20]`: Task criada a partir do Stage 04.
- `[2026-05-07 14:35]`: `AgentState` e `RunBootstrap` implementados e testados; linked agents segue pendente.
- `[2026-05-07 15:10]`: Linked agents e schemas de handoff adicionados ao bootstrap e cobertos por teste.
