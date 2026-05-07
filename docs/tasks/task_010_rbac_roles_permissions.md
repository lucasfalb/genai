# Task: TASK-010 - RBAC por Role e Permissao

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-010 |
| **Group** | AUTH |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_02_auth_rbac.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Esta task define autorizacao por role para separar administradores de tenant, membros e viewers.

## Objectives

- [x] Definir roles suportadas pela aplicacao.
- [x] Mapear roles para permissoes.
- [x] Criar dependencia `require_permission`.
- [x] Testar acesso permitido para `tenant_admin` e negado para `viewer`.

## Non-Goals

- Implementar editor visual de permissoes.
- Implementar roles customizadas por tenant.

## Stage Boundaries

Esta task se limita ao RBAC do Stage 02 e nao altera os contratos de stages posteriores.

## Dependencies

- TASK-009

## Inputs & Contracts

- **Inputs**: `TenantContext` com role efetiva.
- **Outputs**: autorizacao ou erro HTTP de permissao.
- **Schemas**: constantes de roles e permissoes de aplicacao.

## Constraints & Rules

1. Permissoes devem ser avaliadas no backend.
2. Role efetiva deve vir de membership ativo ou regra global de superadmin.
3. Falha de permissao deve retornar erro controlado.

## Implementation Checklist

- [x] Criar enum ou constantes de permissoes.
- [x] Criar mapa role-permission.
- [x] Integrar dependencia de autorizacao.
- [x] Adicionar testes de RBAC.

## Acceptance Criteria

- [x] `tenant_admin` possui permissoes administrativas do tenant.
- [x] `viewer` nao executa acoes administrativas.
- [x] Permissoes sao avaliadas a partir do contexto autenticado.
- [x] Nao ha bypass para usuario comum sem membership.

## Verification

```bash
pytest
```

## Risks & Rollback

- **Risks**: permissoes amplas demais podem permitir mutacoes indevidas.
- **Rollback**: restringir mapa de permissoes e reexecutar testes de autorizacao.

## Execution Log

- `[2026-05-07 12:30]`: Roles, permissoes e dependencia de RBAC implementadas.
