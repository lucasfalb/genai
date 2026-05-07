---
name: genai-task-guardian
description: Generate, update, and validate GenAI project task documentation. Use when Codex is asked to create stage tasks, advance to a new stage, update task status, document architectural decisions in docs/tasks or docs/stages, or verify that task files follow the repository task/stage standard.
---

# GenAI Task Guardian

## Workflow

1. Read the relevant stage file in `docs/stages/` before creating or changing tasks.
2. Read the current stage task index in `docs/tasks/stage_XX_tasks.md` if it exists.
3. For every task listed in a stage index, keep one detailed file named `docs/tasks/task_XXX_slug.md`.
4. Keep the stage index row and detailed task file synchronized for ID, status, priority, and dependency list.
5. Run `python scripts/validate_tasks.py` from the repository root after task documentation changes.
6. Fix validation errors before continuing implementation work.

## Task File Rules

Use `docs/tasks/task_template.md` as the shape. A detailed task file must include:

- Title: `# Task: TASK-XXX - Short title`
- Attribute table: `ID`, `Group`, `Status`, `Stage Ref`, `Spec Ref`, `Priority`, `Owner`, `Created At`, `Updated At`
- Sections: `Context`, `Objectives`, `Non-Goals`, `Stage Boundaries`, `Dependencies`, `Inputs & Contracts`, `Constraints & Rules`, `Implementation Checklist`, `Acceptance Criteria`, `Verification`, `Risks & Rollback`, `Execution Log`
- Checklist markers only: `[ ]`, `[~]`, `[x]`
- Execution log format: `- `[YYYY-MM-DD HH:MM]`: event`
- `COMPLETED` tasks must not contain `[ ]` or `[~]` items in `Objectives`, `Implementation Checklist`, or `Acceptance Criteria`.

Use ASCII Portuguese unless an existing file clearly uses another encoding. Prefer `Concluido`, `Permissao`, `Verificacao`, and similar ASCII spellings to avoid mojibake.

## Stage Index Rules

Stage task files live at `docs/tasks/stage_XX_tasks.md` and must include a table with:

```markdown
| ID | Task | Status | Priority | Depends On |
```

Every task row must link to its detailed task file:

```markdown
| TASK-013 | [Short Task Title](task_013_short_task_title.md) | PENDING | HIGH | TASK-012 |
```

Use statuses `PENDING`, `IN_PROGRESS`, `BLOCKED`, or `COMPLETED`. Use priorities `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`.

## Documentation Discipline

When implementation changes platform behavior, update both the detailed task and the stage document. Record architecture decisions in `docs/stages/stage_XX_*.md` and the task `Execution Log`.

For the current project, preserve this rule: superadmin is a global actor with full tenant control, not a visible tenant member. Tenant-scoped changes by superadmin must still appear in tenant audit/version records with actor context.

## Validation

Run:

```bash
python scripts/validate_tasks.py
```

The validator checks detailed task structure, stage index consistency, and status/checklist coherence. Treat validator failures as documentation defects to fix before moving to the next implementation stage.

For validator expectations and examples, read `references/task-documentation-standard.md` only if more detail is needed.
