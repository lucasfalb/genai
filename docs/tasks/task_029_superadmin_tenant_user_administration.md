# Task: TASK-029 - Superadmin Tenant e User Administration

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-029 |
| **Group** | CORE |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_05_base_multitenant_workflows.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | CRITICAL |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

O roadmap base exige CRUD de tenants e users por superadmin. Hoje o superadmin existe, mas nao ha endpoints para administrar tenants e usuarios globais.

## Objectives

- [ ] Criar CRUD superadmin de tenants.
- [ ] Criar listagem e atualizacao segura de usuarios globais.
- [ ] Permitir ativar, suspender e marcar superadmin com regras explicitas.
- [ ] Registrar auditoria global e tenant-scoped quando aplicavel.

## Non-Goals

- Billing, planos ou quotas.
- UI de superadmin.

## Stage Boundaries

Esta task cobre administracao global necessaria para operar tenants e usuarios.

## Dependencies

- TASK-012

## Inputs & Contracts

- **Inputs**: payloads de tenant, filtros de usuario e status.
- **Outputs**: tenants/users sem segredos e com status atualizado.
- **Schemas**: endpoints `superadmin/tenants` e `superadmin/users`.

## Constraints & Rules

1. Endpoints devem usar `require_superadmin`.
2. Password hashes e refresh tokens nunca devem ser retornados.
3. Mutacoes devem registrar audit log com actor superadmin.
4. Bruno deve cobrir todos os endpoints criados.

## Implementation Checklist

- [ ] Criar repositorios de tenants e users administrativos.
- [ ] Criar endpoints superadmin de tenants.
- [ ] Criar endpoints superadmin de users.
- [ ] Testar permissoes e payloads seguros.
- [ ] Atualizar Bruno e OpenAPI.

## Acceptance Criteria

- [ ] Superadmin cria, lista, atualiza e suspende tenants.
- [ ] Superadmin lista usuarios sem campos sensiveis.
- [ ] Usuario comum nao acessa endpoints.
- [ ] Mutacoes geram audit logs.

## Verification

```bash
cd backend
pytest tests/test_stage_05_superadmin_admin.py
cd ..
backend\.venv\Scripts\python scripts\validate_openapi.py
```

## Risks & Rollback

- **Risks**: endpoint global mal protegido permite controle indevido da plataforma.
- **Rollback**: remover roteador superadmin de tenants/users.

## Execution Log

- `[2026-05-07 15:40]`: Task criada para cobrir CRUD base de tenants e users do roadmap.
