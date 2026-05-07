# Task: TASK-040 - Prompt Cache Invalidation em Mutacoes de Instancia

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-040 |
| **Group** | ENGINE |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_05_prompts.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O `PromptCache` tem TTL de 600s. Qualquer alteracao administrativa que afete o prompt sanduiche (core_prompt, model, temperature, skill/tool ativada/desativada, linked_agent adicionado/removido) deve invalidar o cache imediatamente para garantir que o proximo run use o prompt atualizado.

## Objectives

- [ ] Chamar `PromptCache.invalidate(tenant_id, instance_id)` nos endpoints de mutacao de instancia: update e archive em `tenant_agent_instances.py`.
- [ ] Chamar `PromptCache.invalidate` em ativacao/desativacao de skill (`registry/instances/{id}/skills/{slug}`).
- [ ] Chamar `PromptCache.invalidate` em ativacao/desativacao de tool (`registry/instances/{id}/tools/{slug}`).
- [ ] Garantir que `ToolMetadataCache.invalidate` ja existente e `PromptCache.invalidate` sejam chamados juntos.
- [ ] Testar que apos mutacao o cache nao retorna prompt antigo.

## Non-Goals

- Invalidacao de cache de credenciais (escopo diferente).
- Invalidacao em mutacoes de linked_agents (TASK-049/050 — handoff stage).

## Stage Boundaries

Apenas adicionar chamadas de invalidacao em endpoints ja existentes. Nenhuma nova rota.

## Dependencies

- TASK-036 (PromptCache — disponibiliza `invalidate`)
- TASK-032 (tenant_agent_instances.py — endpoints a serem atualizados)

## Inputs & Contracts

- **Inputs**: `tenant_id`, `instance_id` extraidos do contexto de cada mutacao.
- **Outputs**: chave Redis `tenant:{tenant_id}:instance:{instance_id}:system_prompt` removida.
- **Schemas**: nenhum novo schema.

## Constraints & Rules

1. `PromptCache.invalidate` deve ser chamado na mesma transacao logica que `ToolMetadataCache.invalidate`.
2. Falha de invalidacao de cache nao deve reverter a transacao de banco.
3. Invalidacao deve cobrir todas as mutacoes que alteram o prompt composto.

## Implementation Checklist

- [ ] Atualizar `_after_instance_mutation` em `tenant_agent_instances.py` para chamar `PromptCache.invalidate`.
- [ ] Atualizar endpoint de ativacao de skill para chamar `PromptCache.invalidate`.
- [ ] Atualizar endpoint de desativacao de skill para chamar `PromptCache.invalidate`.
- [ ] Atualizar endpoints de ativacao/desativacao de tool analogamente.
- [ ] Testar: apos PATCH de instancia, `PromptCache.get` retorna None.

## Acceptance Criteria

- [ ] PATCH de instancia invalida tanto `ToolMetadataCache` quanto `PromptCache`.
- [ ] Ativacao de skill invalida `PromptCache` da instancia afetada.
- [ ] Cache miss apos invalidacao forca recomposicao no proximo `PromptBuilder.build`.

## Verification

```bash
cd backend
pytest tests/test_prompt_cache_invalidation.py
```

## Risks & Rollback

- **Risks**: se invalidacao falhar silenciosamente, instancia usa prompt desatualizado ate TTL.
- **Rollback**: reduzir TTL do `PromptCache` para 60s como mitigacao temporaria.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para garantir invalidacao de prompt cache em todas as mutacoes administrativas.
