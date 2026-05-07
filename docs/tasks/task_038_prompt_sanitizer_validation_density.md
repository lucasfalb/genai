# Task: TASK-038 - PromptSanitizer - Validacao e Densidade

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-038 |
| **Group** | ENGINE |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_05_prompts.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Um prompt sanduiche com muitas skills, tools e hand-offs pode exceder o budget de tokens ou conter instrucoes conflitantes. O `PromptSanitizer` valida o prompt composto antes de cachear e retorna um nivel de saude (`ok`, `warning`, `critical`, `blocked`) para observabilidade.

## Objectives

- [x] Implementar `PromptSanitizer` em `engine/prompt_sanitizer.py`.
- [x] Contar tokens com `tiktoken` (modelo `cl100k_base`).
- [x] Calcular `PromptDensity` via `InstructionDensityScorer`.
- [x] Detectar nomes duplicados de skills, tools e hand-offs com `PromptConflictDetector`.
- [x] Levantar `PromptValidationError` se tokens > `MAX_SYSTEM_TOKENS`, nome duplicado ou conflito explicito.
- [x] Emitir evento de alerta via log estruturado em warning e critical.
- [x] Integrar chamada de `PromptSanitizer.validate()` dentro do `PromptBuilder.build()`.

## Non-Goals

- Reparo automatico do prompt (remocao de blocos opcionais).
- Frontend de densidade visivel no dashboard.

## Stage Boundaries

Sanitizacao pura - sem acesso direto ao banco ou Redis nesta task.

## Dependencies

- TASK-037 (PromptBuilder - ponto de chamada do sanitizer)

## Inputs & Contracts

- **Inputs**: `SystemPrompt`, metadata ativa de skills/tools e hand-offs.
- **Outputs**: `SystemPrompt` validado com `density` anexado ou `PromptValidationError`.
- **Schemas**: `PromptDensity(score, level, capability_count, imperative_count, token_count, max_tokens, budget_ratio)`.

## Constraints & Rules

1. `MAX_SYSTEM_TOKENS = 6000`.
2. `WARNING_RATIO = 0.60`, `CRITICAL_RATIO = 0.80`.
3. Score de densidade: `capability_count * 2 + imperative_count + token_count / 1000`.
4. Level critical: score >= 35 ou budget >= 80%.
5. Level warning: score >= 22 ou budget >= 60%.
6. Level blocked: prompt acima do limite maximo e bloqueado por `PromptValidationError`.
7. Nomes de skills, tools ou hand-offs duplicados levantam `PromptValidationError`.
8. Conflitos explicitos do tipo sempre/nunca ou always/never para a mesma instrucao levantam `PromptValidationError`.

## Implementation Checklist

- [x] Adicionar dependencia `tiktoken` ao `pyproject.toml`.
- [x] Criar `engine/prompt_sanitizer.py` com `PromptSanitizer`, `InstructionDensityScorer`, `PromptConflictDetector`.
- [x] Criar excecao `PromptValidationError`.
- [x] Integrar `PromptSanitizer.validate(prompt, metadata)` no `PromptBuilder.build()` antes de chamar `PromptCache.set`.
- [x] Persistir no cache apenas prompts validados com `PromptDensity`.
- [x] Testar: prompt acima de 6000 tokens levanta erro, duplicidade incluindo hand-off levanta erro, warning/critical emitem log estruturado.

## Acceptance Criteria

- [x] Prompt com tokens > 6000 levanta `PromptValidationError`.
- [x] Dois capabilities com mesmo nome callable levantam `PromptValidationError`.
- [x] Tool e hand-off com mesmo nome levantam `PromptValidationError`.
- [x] Instrucao explicita conflitante levanta `PromptValidationError`.
- [x] Prompt valido entre 60-80% do budget emite log de warning sem interromper execucao.
- [x] `PromptDensity.level` correto para score e budget.

## Verification

```bash
cd backend
pytest tests/test_prompt_sanitizer.py
pytest tests/test_stage_05_prompt_runtime.py tests/test_prompt_builder.py tests/test_prompt_cache.py
```

## Risks & Rollback

- **Risks**: `MAX_SYSTEM_TOKENS` muito conservador bloqueia instancias legitimas com muitas skills.
- **Rollback**: aumentar limite ou desabilitar sanitizer (retornar prompt sem validar).

## Execution Log

- `[2026-05-07 00:00]`: Task criada para validacao e density scoring do prompt composto.
- `[2026-05-07 12:30]`: Implementada reescrita completa do `PromptSanitizer` com `InstructionDensityScorer`, `PromptConflictDetector`, `PromptValidationError`, logs estruturados e integracao com `PromptBuilder.build()`.
- `[2026-05-07 20:40]`: Revisao endureceu a implementacao: `validate()` retorna `SystemPrompt` validado com `density`, metadata inclui hand-offs, duplicidade cobre skill/tool/handoff, conflitos explicitos always/never e sempre/nunca bloqueiam o prompt, logs usam campos estruturados e testes cobrem cache, builder, runtime e sanitizer.
