# Task: TASK-033 - Workflow Audit Versions e Cache Invalidation

| Atributo | Valor |
| :--- | :--- |
| **ID** | TASK-033 |
| **Group** | SECURITY |
| **Status** | PENDING |
| **Stage Ref** | `docs/stages/stage_05_base_multitenant_workflows.md` |
| **Spec Ref** | `docs/platform_technical_spec.md` |
| **Priority** | HIGH |
| **Owner** | Unassigned |
| **Created At** | 2026-05-07 |
| **Updated At** | 2026-05-07 |

## Context

Os workflows base alteram usuarios, tenants, memberships, convites e instancias. Essas mutacoes precisam de trilha auditavel, versionamento quando aplicavel e invalidacao de caches de RBAC/metadata.

## Objectives

- [ ] Padronizar helper de auditoria para workflows administrativos.
- [ ] Registrar resource versions para mutacoes versionaveis.
- [ ] Invalidar caches de membership e metadata apos mutacoes.
- [ ] Garantir actor context correto para superadmin.

## Non-Goals

- Observabilidade Prometheus completa.
- Retencao enterprise de auditoria.

## Stage Boundaries

Esta task atua como camada transversal dos workflows do Stage 05.

## Dependencies

- TASK-029
- TASK-030
- TASK-031
- TASK-032

## Inputs & Contracts

- **Inputs**: actor context, tenant id afetado, recurso, snapshot e metadata.
- **Outputs**: audit logs, resource versions e caches invalidados.
- **Schemas**: `audit_logs`, `resource_versions`, chaves Redis de membership/metadata.

## Constraints & Rules

1. Superadmin tenant-scoped deve aparecer em audit/version como ator, mas nao como membro.
2. Metadata auditada deve passar por redaction.
3. Mutacoes de membership invalidam cache `membership:{user_id}:{tenant_id}`.
4. Mutacoes de instancia invalidam cache de metadata da instancia.

## Implementation Checklist

- [ ] Criar helper ou service de workflow audit.
- [ ] Integrar helper nos endpoints do Stage 05.
- [ ] Testar actor_type/actor_role de superadmin.
- [ ] Testar redaction de metadata sensivel.
- [ ] Testar invalidacao de cache.

## Acceptance Criteria

- [ ] Mutacoes administrativas geram audit log.
- [ ] Recursos versionaveis geram `resource_versions`.
- [ ] Superadmin aparece como ator em logs do tenant.
- [ ] Caches afetados sao invalidados.

## Verification

```bash
cd backend
pytest tests/test_stage_05_workflow_audit.py
```

## Risks & Rollback

- **Risks**: falta de auditoria reduz rastreabilidade de operacoes criticas.
- **Rollback**: bloquear mutacoes administrativas ate restaurar audit/version.

## Execution Log

- `[2026-05-07 15:40]`: Task criada para amarrar auditoria, versions e cache dos workflows base.
