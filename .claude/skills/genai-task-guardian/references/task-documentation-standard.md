# Task Documentation Standard

## Required Paths

- Stage specification: `docs/stages/stage_XX_name.md`
- Stage task index: `docs/tasks/stage_XX_tasks.md`
- Detailed task: `docs/tasks/task_XXX_slug.md`
- Validator: `scripts/validate_tasks.py`

## Groups

Allowed `Group` values:

- `CORE`
- `AUTH`
- `REGISTRY`
- `ENGINE`
- `PROMPTS`
- `RAG`
- `HANDOFF`
- `CHANNELS`
- `OBSERVABILITY`
- `SECURITY`

## Status Flow

- `PENDING`: documented but not started.
- `IN_PROGRESS`: implementation or validation is underway.
- `BLOCKED`: cannot proceed until a dependency is resolved.
- `COMPLETED`: implementation, documentation, and verification are complete.

## Checklist Semantics

- `[ ]`: pending.
- `[~]`: in progress.
- `[x]`: completed.

Do not use Unicode checkmarks in new files.

## Validation Command

Run from the repository root:

```bash
python scripts/validate_tasks.py
```

Use `python scripts/validate_tasks.py --root <repo>` when validating from another working directory.
