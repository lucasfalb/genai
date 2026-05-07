# Task: TASK-038 - PromptSanitizer — Validacao e Densidade

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-038 |
| **Group** | ENGINE |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_05_prompts.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Um prompt sanduiche com muitas skills, tools e hand-offs pode exceder o budget de tokens ou conter instrucoes conflitantes. O `PromptSanitizer` valida o prompt composto antes de cachear e retorna um nivel de saude (ok/warning/critical/blocked) para observabilidade.

## Objectives

- [ ] Implementar `PromptSanitizer` em `engine/prompt_sanitizer.py`.
- [ ] Contar tokens com `tiktoken` (modelo `cl100k_base`).
- [ ] Calcular `PromptDensity` via `InstructionDensityScorer`.
- [ ] Detectar nomes de tools duplicados com `PromptConflictDetector`.
- [ ] Levantar `PromptValidationError` se tokens > `MAX_SYSTEM_TOKENS` ou conflito explicito.
- [ ] Emitir evento de alerta (log estruturado) em warning e critical.
- [ ] Integrar chamada de `PromptSanitizer.validate()` dentro do `PromptBuilder.build()`.

## Non-Goals

- Reparo automatico do prompt (remocao de blocos opcionais).
- Frontend de densidade visivel no dashboard.

## Stage Boundaries

Sanitizacao pura — sem acesso direto ao banco ou Redis nesta task.

## Dependencies

- TASK-037 (PromptBuilder — ponto de chamada do sanitizer)

## Inputs & Contracts

- **Inputs**: `SystemPrompt`, `ToolMetadata`.
- **Outputs**: `SystemPrompt` validado ou `PromptValidationError`.
- **Schemas**: `PromptDensity(score, level, capability_count, imperative_count, token_count)`.

## Constraints & Rules

1. `MAX_SYSTEM_TOKENS = 6000`.
2. `WARNING_RATIO = 0.60`, `CRITICAL_RATIO = 0.80`.
3. Score de densidade: `capability_count * 2 + imperative_count + token_count / 1000`.
4. Level critical: score >= 35 ou budget >= 80%.
5. Level warning: score >= 22 ou budget >= 60%.
6. Nomes de tools/hand-offs duplicados levantam `PromptValidationError`.

## Implementation Checklist

- [ ] Adicionar dependencia `tiktoken` ao `pyproject.toml`.
- [ ] Criar `engine/prompt_sanitizer.py` com `PromptSanitizer`, `InstructionDensityScorer`, `PromptConflictDetector`.
- [ ] Criar excecao `PromptValidationError`.
- [ ] Integrar `PromptSanitizer.validate(prompt, metadata)` no `PromptBuilder.build()` antes de chamar `PromptCache.set`.
- [ ] Testar: prompt acima de 6000 tokens levanta erro, tool duplicada levanta erro, warning emitido entre 60-80% budget.

## Acceptance Criteria

- [ ] Prompt com tokens > 6000 levanta `PromptValidationError`.
- [ ] Dois tools com mesmo nome levantam `PromptValidationError`.
- [ ] Prompt valido entre 60-80% do budget emite log de warning sem interromper execucao.
- [ ] `PromptDensity.level` correto para cada faixa de score.

## Verification

```bash
cd backend
pytest tests/test_prompt_sanitizer.py
```

## Risks & Rollback

- **Risks**: `MAX_SYSTEM_TOKENS` muito conservador bloqueia instancias legitimas com muitas skills.
- **Rollback**: aumentar limite ou desabilitar sanitizer (retornar prompt sem validar).

## Execution Log

- `[2026-05-07 00:00]`: Task criada para validacao e density scoring do prompt composto.
