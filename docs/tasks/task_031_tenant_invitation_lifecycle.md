# Task: TASK-031 - Tenant Invitation Lifecycle

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-031 |
| **Group** | AUTH |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_05_base_multitenant_workflows.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

A tabela `invitations` existe, mas faltava fluxo para criar, reenviar, cancelar, validar e aceitar convites de tenant.

## Objectives

- [x] Criar endpoints tenant-scoped de criacao/listagem/cancelamento de convites.
- [x] Criar endpoint publico para validar convite por token.
- [x] Criar endpoint para aceitar convite e criar membership.
- [x] Integrar template `tenant_invitation` e email outbox.

## Non-Goals

- UI de aceite de convite.
- Provisionamento de tenant via billing.
- Provider SMTP real/worker de entrega; esta task valida outbox persistida e configuracao SMTP.

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

- [x] Criar repository de invitations.
- [x] Criar endpoints tenant-scoped de invite.
- [x] Criar endpoints publicos de validate/accept.
- [x] Integrar membership creation e cache invalidation.
- [x] Atualizar Bruno e OpenAPI.

## Acceptance Criteria

- [x] Tenant admin cria convite para role permitida.
- [x] Convite cancelado, expirado ou usado nao pode ser aceito.
- [x] Aceite cria membership ativa no tenant correto.
- [x] Superadmin nao aparece como membro apos convidar.

## Verification

```bash
cd backend
pytest tests/test_stage_05_invitations.py
pytest
cd ..
backend\.venv\Scripts\python scripts\validate_openapi.py
python scripts\validate_tasks.py
```

## Risks & Rollback

- **Risks**: aceite de convite cross-tenant pode violar isolamento.
- **Rollback**: suspender aceite de convites e invalidar tokens pendentes.

## Execution Log

- `[2026-05-07 15:40]`: Task criada para cobrir lifecycle de convites pendente desde Stage 01/02.
- `[2026-05-07 20:05]`: Implementados repository, endpoints tenant-scoped/publicos, email outbox `tenant_invitation`, aceite com criacao/ativacao de usuario, membership ativa, cache invalidation, audit/version e Bruno.
- `[2026-05-07 20:05]`: SMTP adicionado como configuracao de runtime; validacao automatizada cobre outbox/template/payload, sem disparo real para provider externo.
