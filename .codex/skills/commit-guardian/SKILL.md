---
name: commit-guardian
description: Standardize commit planning, commit messages, and commit descriptions for the GenAI project. Use when Codex is asked to create, review, name, describe, squash, split, or prepare commits, PR summaries, changelog-style summaries, or any git commit message.
---

# Commit Guardian

## Workflow

1. Inspect the changed files before writing a commit message.
2. Separate unrelated changes into distinct commits when the user asks to commit and the work spans multiple concerns.
3. Preserve user changes. Never revert unrelated files just to make a commit cleaner.
4. Use Conventional Commits for the subject.
5. Reference tasks/stages when the change implements documented work.
6. Keep the message factual and implementation-focused.
7. If actually committing, run relevant validation first unless the user explicitly says to skip tests.
8. **Never add `Co-Authored-By`, `Co-authored-by`, or any AI/tool attribution to commit messages.** Commits are authored solely by the developer.

## Subject Format

Use:

```text
<type>(<scope>): <summary>
```

Rules:

- Use lowercase `type`.
- Use a short lowercase `scope` when it clarifies the affected area.
- Keep the subject at or under 72 characters when practical.
- Use imperative present tense in English.
- Do not end with a period.
- Do not use emojis.

Allowed types:

- `feat`: new behavior or endpoint.
- `fix`: bug fix or behavioral correction.
- `docs`: documentation, tasks, Bruno collection, examples.
- `test`: tests only.
- `refactor`: internal change without behavior change.
- `chore`: tooling, dependencies, scripts, maintenance.
- `build`: packaging, Docker, dependency/build config.
- `ci`: CI/CD configuration.
- `perf`: performance improvement.
- `security`: security hardening or auth-sensitive change.

Preferred scopes for this project:

- `auth`
- `tenants`
- `members`
- `registry`
- `engine`
- `rag`
- `handoff`
- `channels`
- `audit`
- `tasks`
- `bruno`
- `docs`
- `db`
- `api`

## Body Format

Add a body when the change is more than trivial.

Use concise bullets:

```text
feat(auth): add account activation flow

- Add single-use activation tokens and email outbox entries.
- Expose activation request and confirmation endpoints.
- Cover pending, expired, and reused token cases.

Refs: TASK-026
```

Body rules:

- Explain what changed and why, not every file touched.
- Mention migrations, new endpoints, new environment variables, or behavior changes.
- Mention validation results when useful.
- Use `Refs: TASK-XXX` for related tasks.
- Use `BREAKING CHANGE:` footer only when consumers must change behavior.

## GenAI Project Requirements

- For task documentation changes, include the task/stage in the body.
- For endpoint changes, confirm Bruno request coverage in `genai-endpoints/`.
- For auth, tenant, RBAC, audit, or secret-handling changes, prefer `security` or a clear auth-related `feat/fix` with security notes in the body.
- For database migrations, mention the migration purpose in the body.
- For generated lockfiles or dependency changes, use `build` or `chore` unless behavior changes.

## Commit Splitting

Split commits when changes are independently reviewable:

- Schema/migration separate from API behavior when large.
- Backend implementation separate from docs/tasks when both are substantial.
- Bruno collection updates may stay with endpoint changes when they document the same contract.
- Test-only follow-up uses `test(scope): ...`.

Do not split when a small docs/test update is necessary to validate the same code change.

## Review Checklist

Before finalizing a commit message, verify:

- Subject accurately describes the primary change.
- Type and scope match the files changed.
- Body references tasks when applicable.
- No secrets, tokens, credentials, or private values appear.
- Validation status is known if the user expects a commit-ready result.

## Examples

```text
docs(tasks): add base multitenant workflow stage
```

```text
feat(engine): add base LangGraph routing

- Compile the Stage 04 graph with rag, llm, dispatch, and handoff nodes.
- Cover respond, tool call, and handoff routes in tests.

Refs: TASK-023
```

```text
security(auth): add single-use password reset tokens

- Store only token hashes with expiration and consumed timestamps.
- Revoke existing refresh tokens after password reset.
- Add Bruno requests for forgot and reset flows.

Refs: TASK-027
```
