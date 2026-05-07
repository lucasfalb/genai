# Task: TASK-037 - PromptBuilder — Montagem Sanduiche

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-037 |
| **Group** | ENGINE |
| **Status** | DONE |
| **Stage Ref** | `docs/stages/stage_05_prompts.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O prompt do agente e composto dinamicamente em tres camadas: core prompt da instancia, blocos de instrucao de skills/tools ativas e constraints fixas. O `PromptBuilder` monta esse sanduiche consultando o `ToolMetadataCache` e cacheia o resultado via `PromptCache`.

## Objectives

- [x] Implementar `PromptBuilder` em `engine/prompt_builder.py`.
- [x] Camada 1: `instance.core_prompt`.
- [x] Camada 2: `skill.definition.prompt_block` por skill ativa + `tool.definition.prompt_block` por tool ativa + descricao de hand-off por `linked_agent`.
- [x] Camada 3: constraints fixas de idioma e integridade.
- [x] Retornar `SystemPrompt` cacheado ou recomposto.
- [x] Testar montagem com skills/tools/linked_agents variaveis.

## Non-Goals

- Sanitizacao e density scoring (TASK-038).
- Integracao LLM real (TASK-039).
- Invalidacao em mutacoes administrativas (TASK-040).

## Stage Boundaries

Apenas montagem e cache do prompt. Nao cria endpoints nem altera banco.

## Dependencies

- TASK-015 (ToolMetadataCache — fonte de skills, tools e linked_agents por instancia)
- TASK-036 (SystemPrompt schema e PromptCache)

## Inputs & Contracts

- **Inputs**: `instance_id`, `tenant_id`, conexao de banco e Redis.
- **Outputs**: `SystemPrompt` com `core`, `tool_instructions`, `constraints` e `full`.
- **Schemas**: `ToolMetadata.active_skills`, `ToolMetadata.active_tools`, `ToolMetadata.linked_agents`.

## Constraints & Rules

1. `PromptBuilder.build()` deve checar `PromptCache` antes de consultar banco.
2. Agentes vinculados aparecem como instrucao de tool fantasma na Camada 2.
3. `full` = `f"{core}\n\n{tool_instructions}\n\n{constraints}".strip()`.
4. Prompt composto deve ser salvo no cache apos cada recomposicao.

## Implementation Checklist

- [x] Criar `engine/prompt_builder.py` com `PromptBuilder(connection)`.
- [x] Implementar `build(tenant_id, instance_id, core_prompt, linked_agents) -> SystemPrompt`.
- [x] Checar `PromptCache.get` no inicio; chamar `PromptCache.set` no fim.
- [x] Montar `tool_section` a partir de `active_skills`, `active_tools` e `linked_agents`.
- [x] Implementar `assemble()` estatico com constraints fixas.
- [x] Testar: cache hit evita consulta ao banco, montagem correta com 0/N skills/tools/links.

## Acceptance Criteria

- [x] `PromptBuilder.build` retorna `SystemPrompt.full` nao vazio para instancia com core_prompt.
- [x] Cache hit nao dispara queries ao banco.
- [x] `tool_instructions` contem blocos de todas as skills/tools ativas.
- [x] Agente vinculado aparece como instrucao de hand-off na Camada 2.

## Verification

```bash
cd backend
pytest tests/test_prompt_builder.py
```

## Risks & Rollback

- **Risks**: cache hit com prompt desatualizado ate TTL expirar ou invalidacao explicita.
- **Rollback**: zerar TTL em `PromptCache` ou forcar `invalidate` antes de cada build.

## Execution Log

- `[2026-05-07 00:00]`: Task criada para implementar montagem do prompt sanduiche.
- `[2026-05-07 00:01]`: Implementada — PromptBuilder reescrito com assemble() estatico e build() async cache-aware; PromptCache.get() refatorado para retornar SystemPrompt|None puro; bootstrap.py atualizado; tests/test_prompt_builder.py (10 testes). 110 testes passando.
