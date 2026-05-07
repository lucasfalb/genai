# Task: TASK-040 - Prompt Cache Invalidation em Mutacoes de Instancia

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-040 |
| **Group** | ENGINE |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_05_prompts.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Codex |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O `PromptCache` tem TTL de 600s. Qualquer alteracao administrativa que afete o prompt sanduiche precisa invalidar o cache imediatamente para garantir que o proximo run use o prompt atualizado.

As mutacoes cobertas nesta task sao:

- Alteracao ou arquivamento de `agent_instances`.
- Ativacao/desativacao de skill em uma instancia.
- Ativacao/desativacao de tool em uma instancia.

## Objectives

- [x] Chamar `PromptCache.invalidate(tenant_id, instance_id)` nos endpoints de update e archive em `tenant_agent_instances.py`.
- [x] Chamar `PromptCache.invalidate` na ativacao/desativacao de skill em `registry/instances/{id}/skills/{slug}`.
- [x] Chamar `PromptCache.invalidate` na ativacao/desativacao de tool em `registry/instances/{id}/tools/{slug}`.
- [x] Garantir que `ToolMetadataCache.invalidate` e `PromptCache.invalidate` sejam chamados juntos.
- [x] Testar que mutacoes administrativas invalidam o prompt cache da instancia afetada.

## Non-Goals

- [x] Invalidacao de cache de credenciais.
- [x] Invalidacao em mutacoes de linked agents, que pertence ao stage de handoff.
- [x] Criar novas rotas.

## Stage Boundaries

Apenas adiciona chamadas de invalidacao em endpoints ja existentes. Nenhuma nova rota ou schema foi criado.

## Dependencies

- TASK-036
- TASK-032

## Inputs & Contracts

- **Inputs**: `tenant_id`, `instance_id` extraidos do contexto de cada mutacao.
- **Outputs**: chave Redis `tenant:{tenant_id}:instance:{instance_id}:system_prompt` removida.
- **Schemas**: nenhum novo schema.
- **Endpoint behavior**: respostas seguem os envelopes existentes; a mudanca e apenas invalidacao de cache.

## Constraints & Rules

1. `PromptCache.invalidate` deve ser chamado junto de `ToolMetadataCache.invalidate`.
2. Falha de invalidacao de cache nao deve reverter a transacao de banco, conforme contrato dos caches.
3. Invalidacao deve cobrir todas as mutacoes que alteram o prompt composto neste stage.

## Implementation Checklist

- [x] Atualizar mutacoes de `tenant_agent_instances.py` para chamar `PromptCache.invalidate`.
- [x] Atualizar endpoint de ativacao/desativacao de skill para chamar `PromptCache.invalidate`.
- [x] Atualizar endpoint de ativacao/desativacao de tool para chamar `PromptCache.invalidate`.
- [x] Atualizar descricoes OpenAPI das rotas afetadas.
- [x] Cobrir invalidacao em testes de instancias e registry.

## Acceptance Criteria

- [x] PATCH de instancia invalida tanto `ToolMetadataCache` quanto `PromptCache`.
- [x] Archive de instancia invalida tanto `ToolMetadataCache` quanto `PromptCache`.
- [x] Ativacao/desativacao de skill invalida `PromptCache` da instancia afetada.
- [x] Ativacao/desativacao de tool invalida `PromptCache` da instancia afetada.
- [x] Cache miss apos invalidacao forca recomposicao no proximo `PromptBuilder.build`.

## Verification

```bash
cd backend
.\.venv\Scripts\python -m pytest tests/test_stage_03_registry.py tests/test_stage_05_agent_instances.py tests/test_prompt_cache.py -q
backend\.venv\Scripts\python scripts\validate_openapi.py
python scripts\validate_tasks.py
```

## Risks & Rollback

- **Risks**: se invalidacao falhar silenciosamente por indisponibilidade do Redis, a instancia pode usar prompt desatualizado ate o TTL expirar.
- **Rollback**: remover chamadas de `PromptCache.invalidate` e reduzir temporariamente o TTL do `PromptCache` para 60s.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para garantir invalidacao de prompt cache em todas as mutacoes administrativas.
- `[2026-05-08 00:00]`: Mutacoes de instancia e registry passaram a invalidar `ToolMetadataCache` e `PromptCache` em conjunto.
- `[2026-05-08 00:00]`: Testes focados de registry, agent instances e prompt cache passaram com 19 testes.
