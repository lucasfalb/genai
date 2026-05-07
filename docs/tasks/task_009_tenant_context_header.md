# Task: TASK-009 - Tenant Context por X-Tenant-ID

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-009 |
| **Group** | AUTH |
| **Status** | COMPLETED |
| **Stage Ref** | `docs/stages/stage_02_auth_rbac.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Esta task liga autenticacao de aplicacao ao isolamento tenant-scoped exigido pelo Stage 01.

## Objectives

- [x] Exigir header `X-Tenant-ID` em dependencias tenant-scoped.
- [x] Validar membership ativo para usuarios comuns.
- [x] Configurar `app.current_tenant_id` na conexao PostgreSQL.
- [x] Adicionar cache Redis de membership com fallback para PostgreSQL.

## Non-Goals

- Criar CRUD completo de tenants.
- Implementar UI de troca de tenant.

## Stage Boundaries

Esta task pertence ao Stage 02, mas integra diretamente o contrato de RLS criado no Stage 01.

## Dependencies

- TASK-004
- TASK-008

## Inputs & Contracts

- **Inputs**: JWT Bearer e header `X-Tenant-ID`.
- **Outputs**: `TenantContext` com `tenant_id`, `user_id` e role efetiva.
- **Schemas**: memberships e configuracao de sessao PostgreSQL.

## Constraints & Rules

1. Query tenant-scoped deve receber tenant context valido.
2. Usuario comum sem membership ativo deve ser rejeitado.
3. Cache Redis nunca deve ser a unica fonte de autorizacao.

## Implementation Checklist

- [x] Criar dependencia de usuario autenticado.
- [x] Criar dependencia de tenant context.
- [x] Integrar Redis para cache de membership.
- [x] Testar acesso permitido e negado por tenant.

## Acceptance Criteria

- [x] Requests sem `X-Tenant-ID` sao rejeitados em rotas tenant-scoped.
- [x] Membership ativo libera acesso ao tenant correto.
- [x] RLS recebe tenant id via configuracao de sessao.
- [x] Fallback para PostgreSQL funciona sem cache.

## Verification

```bash
pytest
```

## Risks & Rollback

- **Risks**: contexto de tenant incorreto pode vazar dados entre tenants.
- **Rollback**: remover dependencias tenant-scoped novas e invalidar cache de memberships.

## Execution Log

- `[2026-05-07 12:30]`: Tenant context por header e cache Redis implementados.
