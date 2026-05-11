# Task: TASK-079 - Per-Instance Constraints (Backend + Frontend)

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-079 |
| **Group** | ENGINE |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_10_observability.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Codex |
| **Created At** | 2026-05-11 |
| **Updated At** | 2026-05-11 |

## Context

Antes desta task, `### Restrições` era hardcoded em `engine/prompt_builder.py:_CONSTRAINTS` e injetado em todos os runs. Para multi-tenant, cada instância precisa configurar suas próprias restrições explicitamente, similar a instruction_blocks e guardrails. Removeu o hardcode, criou coluna `constraints` em `agent_instances`, e expôs UI dedicada na tab Instructions.

## Objectives

- [x] Adicionar coluna `constraints JSONB NOT NULL DEFAULT '[]'::jsonb` em `agent_instances`.
- [x] Remover constante hardcoded `_CONSTRAINTS` do `PromptBuilder`.
- [x] Atualizar `PromptBuilder.assemble` aceitando `constraints: list[dict]` e formatando em `### Restrições`.
- [x] Atualizar `PromptBuilder.build` + `_get_prompt_config` lendo `constraints` da instância.
- [x] Estender schemas: `AgentConstraint`, `AgentPromptConfigRequest`, `AgentPromptConfigResponse`.
- [x] Estender repository `update_prompt_config`/`get_prompt_config` para incluir `constraints`.
- [x] Estender endpoint `PUT /tenant/instances/{id}/prompt-config`.
- [x] Tipos frontend `AgentConstraint`.
- [x] Componente `lib/components/instance/constraints.svelte` (accordion + add/remove/toggle/priority).
- [x] Integrar componente na tab Instructions.
- [x] Garantir `+page.svelte` (overview shortcut) passa `constraints` ao salvar prompt config.
- [x] Atualizar testes de prompt builder (não exige mais `### Restrições` por default).

## Non-Goals

- Não criar UI separada de "playground" de constraints.
- Não migrar dados existentes (constraints default = `[]`).

## Stage Boundaries

Esta task fica entre Stage 05 (prompt runtime original) e Stage 10 (observability). Não toca dispatcher/handoff (Stage 07) nem RAG retriever (que ganhou threshold em mudança separada).

## Dependencies

- TASK-037 (PromptBuilder sandwich)
- TASK-064 (Guardrails customizados — mesma forma estrutural)

## Inputs & Contracts

- **Migration**: `20260511_0017_agent_constraints.py`.
- **Schemas**:
  - `AgentConstraint { id: str, rule: str, priority: int, is_enabled: bool }`
  - `AgentPromptConfigRequest.constraints: list[AgentConstraint]`
  - `AgentPromptConfigResponse.constraints: list[AgentConstraint]`
- **Endpoint**: `PUT /api/v1/tenant/instances/{id}/prompt-config` (mesmo path, payload estendido).
- **Frontend**: `lib/components/instance/constraints.svelte` com binding `constraints = $bindable()`.

## Constraints & Rules

1. Constraints ordenados por `priority` ASC, depois `id`.
2. Constraints com `is_enabled=false` ignorados na montagem do prompt.
3. Sanitizer rejeita `rule` contendo padrões sensíveis (mesma lista de guardrails).
4. Frontend gera `id` automaticamente se ausente.
5. Salvar substitui completamente a lista (replace, not patch).
6. `### Restrições` só aparece no prompt se houver pelo menos uma constraint ativa.

## Implementation Checklist

- [x] Migration aplicada nos DBs `genai` e `genai_test`.
- [x] Backend: schemas, repo, builder, endpoint, sanitizer.
- [x] Frontend: tipos, componente, integração na instructions page e overview shortcut.
- [x] Testes: `test_prompt_builder_core_only` agora valida ausência por default; novo `test_prompt_builder_with_constraints`.
- [x] `npm run check` sem novos erros nos arquivos tocados.

## Acceptance Criteria

- [x] Criar nova instância → constraints `[]`, prompt não contém `### Restrições`.
- [x] Adicionar constraint via UI + salvar → próximo run inclui `### Restrições` com a regra.
- [x] Toggle off de uma constraint → regra some do prompt do próximo run.
- [x] Priority altera ordem de listagem dentro de `### Restrições`.
- [x] Sanitizer rejeita `rule` com `api_key`, `password`, etc.

## Verification

```bash
cd backend
SYNC_DATABASE_URL=postgresql+psycopg://genai:genai@localhost:5432/genai_test .venv/Scripts/alembic upgrade head
.venv/Scripts/python -m pytest tests/test_stage_05_prompt_runtime.py -q
cd ../frontend
npm run check
```

## Risks & Rollback

- **Risco**: instâncias legadas tinham comportamento implícito com `_CONSTRAINTS` hardcoded; após upgrade, perdem essa proteção até admin configurar via UI. Mitigação: comunicar como mudança de contrato; documentar em stage_10.
- **Rollback**: `alembic downgrade 20260511_0016` + reverter `prompt_builder.py` + reverter componentes/types frontend.

## Execution Log

- `[2026-05-11 04:00]`: Constraints hardcoded removidos. Migration `20260511_0017` aplicada nos dois bancos.
- `[2026-05-11 04:10]`: Schemas + repository + endpoint atualizados.
- `[2026-05-11 04:15]`: PromptBuilder.assemble + build aceitando constraints; `_format_constraints` cria `### Restrições` somente quando há entries habilitadas.
- `[2026-05-11 04:20]`: Frontend tipos + componente + integração na Instructions page + fallback no overview shortcut.
- `[2026-05-11 04:25]`: Testes ajustados (56 passing). `npm run check` zero novos erros. Status -> COMPLETED.
