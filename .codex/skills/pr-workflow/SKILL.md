---
name: pr-workflow
description: Branch and PR workflow for the GenAI project. Use when Codex is asked to start a task, create a branch, open a PR, merge to dev, or manage the dev/prod git flow. Enforces task-branch → dev → prod promotion model.
---

# PR Workflow

## Branch Model

```
prod          ← production releases only (merged from dev after validation)
dev           ← integration branch; all task branches merge here
task/TASK-XXX-slug  ← one branch per task, created from dev
```

Never commit directly to `dev` or `prod`. All work happens on task branches.

## Starting a Task

1. Always start from the latest `dev`:

```bash
git checkout dev
git pull origin dev
git checkout -b task/TASK-XXX-slug
```

Branch naming rule: `task/` prefix + uppercase task ID + short kebab-case slug.  
Examples: `task/TASK-041-rag-migrations`, `task/TASK-054-channels-webhook`

2. Implement the task. Follow `docs/tasks/task_XXX_slug.md` for acceptance criteria.

3. Run validation before opening a PR:
```bash
# Backend
cd backend && .venv/bin/python -m pytest -x -q

# Frontend (if changed)
cd frontend && npm run check
```

## Opening a PR (task → dev)

After implementation is complete and tests pass:

```bash
git push -u origin task/TASK-XXX-slug
gh pr create \
  --base dev \
  --title "feat(scope): short description (TASK-XXX)" \
  --body "$(cat <<'EOF'
## Summary
- <bullet 1>
- <bullet 2>

## Acceptance Criteria
- [ ] criterion from task file

## Checklist
- [ ] Tests pass
- [ ] Bruno requests updated (if endpoint changed)
- [ ] Task execution log updated

Refs: TASK-XXX
EOF
)"
```

PR title format: same as commit — `type(scope): summary (TASK-XXX)`.

## Merging to dev

After PR review:

```bash
gh pr merge <PR-number> --squash --delete-branch
```

Use `--squash` to keep `dev` history clean.

## Promoting dev → prod

Only when `dev` is stable and tested end-to-end:

```bash
git checkout prod
git pull origin prod
git merge --no-ff dev -m "chore(release): promote dev to prod — YYYY-MM-DD"
git push origin prod
git tag -a v0.X.Y -m "Release v0.X.Y — <one-line summary>"
git push origin v0.X.Y
```

## Rules

- One task = one branch = one PR. Never bundle unrelated tasks.
- PRs always target `dev`, never `prod` directly.
- Delete task branches after merge (`--delete-branch`).
- If a task branch is stale (> 3 days without commits), rebase from `dev` before opening a PR.
- Never force-push `dev` or `prod`.

## Quick Reference

| Action | Command |
|--------|---------|
| Start task | `git checkout dev && git pull && git checkout -b task/TASK-XXX-slug` |
| Push branch | `git push -u origin task/TASK-XXX-slug` |
| Open PR to dev | `gh pr create --base dev ...` |
| Merge PR | `gh pr merge N --squash --delete-branch` |
| Promote to prod | `git checkout prod && git merge --no-ff dev` |
| Tag release | `git tag -a vX.Y.Z && git push origin vX.Y.Z` |
