# Task: TASK-031 - Tenant Invitation Lifecycle

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-031 |
| **Group** | AUTH |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_05_base_multitenant_workflows.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

A tabela `invitations` existe, mas falta fluxo para criar, reenviar, cancelar, validar e aceitar convites de tenant.

## Objectives

- [ ] Criar endpoints tenant-scoped de criacao/listagem/cancelamento de convites.
- [ ] Criar endpoint publico para validar convite por token.
- [ ] Criar endpoint para aceitar convite e criar membership.
- [ ] Integrar template `tenant_invitation` e email outbox.

## Non-Goals

- UI de aceite de convite.
- Provisionamento de tenant via billing.

## Stage Boundaries

Esta task cobre lifecycle de convites e membership inicial, usando auth lifecycle existente.

## Dependencies

- TASK-025
- TASK-030

## Inputs & Contracts

- **Inputs**: email, role, tenant context e invitation token.
- **Outputs**: invitation records, membership ativa e eventos de email.
- **Schemas**: tabela `invitations`, tokens transacionais e responses de convite.

## Constraints & Rules

1. Convite deve ser single-use e expirar.
2. Aceite deve respeitar email do convite.
3. Role convidada deve estar dentro do RBAC permitido.
4. Superadmin pode convidar em qualquer tenant sem virar membro.

## Implementation Checklist

- [ ] Criar repository de invitations.
- [ ] Criar endpoints tenant-scoped de invite.
- [ ] Criar endpoints publicos de validate/accept.
- [ ] Integrar membership creation e cache invalidation.
- [ ] Atualizar Bruno e OpenAPI.

## Acceptance Criteria

- [ ] Tenant admin cria convite para role permitida.
- [ ] Convite cancelado, expirado ou usado nao pode ser aceito.
- [ ] Aceite cria membership ativa no tenant correto.
- [ ] Superadmin nao aparece como membro apos convidar.

## Verification

```bash
cd backend
pytest tests/test_stage_05_invitations.py
```

## Risks & Rollback

- **Risks**: aceite de convite cross-tenant pode violar isolamento.
- **Rollback**: suspender aceite de convites e invalidar tokens pendentes.

## Execution Log

- `[2026-05-07 15:40]`: Task criada para cobrir lifecycle de convites pendente desde Stage 01/02.
