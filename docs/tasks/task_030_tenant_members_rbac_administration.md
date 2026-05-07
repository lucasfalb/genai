# Task: TASK-030 - Tenant Members e RBAC Administration

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-030 |
| **Group** | AUTH |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_05_base_multitenant_workflows.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Codex |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

RBAC existe no middleware, mas tenant admins ainda nao conseguem listar, alterar role, suspender ou remover membros por endpoint.

## Objectives

- [x] Criar `GET /tenant/members`.
- [x] Criar endpoints para alterar role/status de membership.
- [x] Criar endpoint para remover ou suspender membro.
- [x] Garantir que superadmin nao aparece como membro visivel.

## Non-Goals

- Convite por email, coberto por TASK-031.
- Grupos customizados de permissao.

## Stage Boundaries

Esta task cobre administracao de memberships ja existentes, respeitando RBAC tenant-scoped.

## Dependencies

- TASK-010
- TASK-012

## Inputs & Contracts

- **Inputs**: `X-Tenant-ID`, member id, role/status.
- **Outputs**: lista e mutacoes de membership sem dados sensiveis.
- **Schemas**: Pydantic de member list/update.

## Constraints & Rules

1. Tenant admin pode gerir membros do proprio tenant.
2. Superadmin pode gerir qualquer tenant sem aparecer na listagem.
3. Viewer/member nao podem alterar roles.
4. Toda mutacao invalida cache de membership.

## Implementation Checklist

- [x] Criar repositorio de memberships administrativas.
- [x] Criar endpoints tenant-scoped de members.
- [x] Testar RBAC por role.
- [x] Testar exclusao visual de superadmin.
- [x] Atualizar Bruno e OpenAPI.

## Acceptance Criteria

- [x] `GET /tenant/members` nao retorna superadmin.
- [x] Tenant admin altera role/status validos.
- [x] Cache Redis de membership e invalidado em mutacoes.
- [x] Superadmin age com auditoria, sem membership visivel.

## Verification

```bash
cd backend
pytest tests/test_stage_05_tenant_members.py
```

## Risks & Rollback

- **Risks**: erro em role management pode conceder privilegios indevidos.
- **Rollback**: bloquear endpoints de mutacao e manter listagem read-only.

## Execution Log

- `[2026-05-07 15:40]`: Task criada para cobrir administracao RBAC por tenant.
- `[2026-05-07 19:45]`: Implementacao iniciada para listagem e mutacao de memberships tenant-scoped.
- `[2026-05-07 20:05]`: Endpoints de members, repositorio, Bruno, invalidacao de cache, audit/version e testes implementados.
