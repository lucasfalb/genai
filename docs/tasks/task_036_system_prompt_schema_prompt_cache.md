# Task: TASK-036 - SystemPrompt Schema e PromptCache

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-036 |
| **Group** | ENGINE |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_05_prompts.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O executor atual usa resposta placeholder. Para integrar um LLM real o runtime precisa de um modelo estruturado para o prompt composto e de um cache Redis que evite recomposicao do prompt sanduiche a cada run.

## Objectives

- [x] Criar `SystemPrompt` e `PromptDensity` como modelos Pydantic em `engine/prompt_schema.py`.
- [x] Implementar `PromptCache` em `engine/prompt_cache.py` com `get`, `set` e `invalidate`.
- [x] Usar chave `tenant:{tenant_id}:instance:{instance_id}:system_prompt` com TTL 600s.
- [x] Cobrir cache hit/miss e invalidacao com testes.

## Non-Goals

- Montagem do prompt (PromptBuilder — TASK-037).
- Sanitizacao e density scoring (TASK-038).
- Integracao LLM real (TASK-039).

## Stage Boundaries

Apenas schema e cache. Nenhuma query ao banco ou chamada ao LLM nesta task.

## Dependencies

- TASK-019 (AgentState — define o contexto de run que consome o prompt)
- TASK-020 (Redis session lock — mesma infra Redis)

## Inputs & Contracts

- **Inputs**: `tenant_id`, `instance_id` para chave de cache.
- **Outputs**: `SystemPrompt` serializado em JSON no Redis.
- **Schemas**: `SystemPrompt(core, tool_instructions, constraints, full, density)`, `PromptDensity(score, level, capability_count, imperative_count, token_count, max_tokens, budget_ratio)`.

## Constraints & Rules

1. TTL do prompt composto: 600 segundos.
2. Chave escopada por `tenant_id` e `instance_id` — nunca global.
3. `SystemPrompt` deve ser serializavel com `model_dump_json()` / `model_validate_json()`.
4. Cache miss retorna `None`; caller decide se recalcula.

## Implementation Checklist

- [x] Criar `engine/prompt_schema.py` com `SystemPrompt` e `PromptDensity`.
- [x] Criar `engine/prompt_cache.py` com `PromptCache(redis)` e metodos `get`, `set`, `invalidate`.
- [x] Escrever testes unitarios: cache hit serializa e deserializa corretamente, cache miss retorna None, invalidate remove chave.

## Acceptance Criteria

- [x] `PromptCache.get` retorna `None` em cold cache e `SystemPrompt` valido apos `set`.
- [x] `PromptCache.invalidate` remove a chave do Redis.
- [x] Modelos passam em `model_validate_json(model.model_dump_json())`.

## Verification

```bash
cd backend
pytest tests/test_prompt_cache.py
```

## Risks & Rollback

- **Risks**: TTL muito longo pode servir prompt desatualizado apos mudanca de skill/tool.
- **Rollback**: reduzir TTL ou desabilitar cache (retornar None sempre em `get`).

## Execution Log

- `[2026-05-07 00:00]`: Task criada para definir schema e cache do prompt composto.
- `[2026-05-07 00:01]`: Implementada — `engine/prompt_schema.py` (SystemPrompt, PromptDensity Pydantic), `set()` adicionado ao PromptCache, `tests/test_prompt_cache.py` (8 testes). 100 testes passando.
