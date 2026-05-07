# Task: TASK-027 - Password Recovery e Change Flow

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-027 |
| **Group** | AUTH |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_05_base_multitenant_workflows.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Usuarios precisam recuperar senha sem suporte manual, e usuarios autenticados precisam alterar senha invalidando refresh tokens antigos.

## Objectives

- [ ] Criar endpoint `/auth/password/forgot`.
- [ ] Criar endpoint `/auth/password/reset`.
- [ ] Criar endpoint `/auth/password/change`.
- [ ] Revogar refresh tokens apos reset ou change.

## Non-Goals

- Politica enterprise de MFA.
- SSO ou login social.

## Stage Boundaries

Esta task cobre apenas lifecycle de senha com tokens transacionais e JWT existentes.

## Dependencies

- TASK-025

## Inputs & Contracts

- **Inputs**: email, reset token, senha atual e nova senha.
- **Outputs**: senha atualizada, tokens revogados e email outbox `password_changed`.
- **Schemas**: Pydantic requests/responses de password lifecycle.

## Constraints & Rules

1. `forgot` deve responder de forma neutra para evitar enumeracao.
2. Reset token deve ser single-use e expirar.
3. `change` deve exigir senha atual e Bearer token.
4. Nova senha deve usar o mesmo hashing seguro do registro.

## Implementation Checklist

- [ ] Criar schemas de forgot/reset/change.
- [ ] Criar endpoints de password lifecycle.
- [ ] Integrar revogacao de refresh tokens.
- [ ] Criar email outbox `password_reset` e `password_changed`.
- [ ] Atualizar Bruno e OpenAPI.

## Acceptance Criteria

- [ ] Reset com token valido troca senha e revoga refresh tokens.
- [ ] Token invalido, expirado ou usado e rejeitado.
- [ ] Change exige senha atual correta.
- [ ] Requests Bruno cobrem os tres endpoints.

## Verification

```bash
cd backend
pytest tests/test_stage_05_password_lifecycle.py
cd ..
backend\.venv\Scripts\python scripts\validate_openapi.py
```

## Risks & Rollback

- **Risks**: reset mal protegido permite takeover de conta.
- **Rollback**: desabilitar endpoints de reset/change e exigir fluxo manual temporario.

## Execution Log

- `[2026-05-07 15:40]`: Task criada para cobrir recovery e change de senha.
