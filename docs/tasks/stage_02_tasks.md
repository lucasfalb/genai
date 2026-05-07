# Stage 02 Tasks - Auth, JWT e RBAC

| ID | Task | Status | Priority | Depends On |
| :--- | :--- | :--- | :--- | :--- |
| TASK-007 | [Auth API e Password Hashing](task_007_auth_api_password_hashing.md) | COMPLETED | CRITICAL | TASK-001, TASK-002 |
| TASK-008 | [JWT Access e Refresh Tokens](task_008_jwt_access_refresh_tokens.md) | COMPLETED | CRITICAL | TASK-007 |
| TASK-009 | [Tenant Context por X-Tenant-ID](task_009_tenant_context_header.md) | COMPLETED | CRITICAL | TASK-004, TASK-008 |
| TASK-010 | [RBAC por Role e Permissao](task_010_rbac_roles_permissions.md) | COMPLETED | HIGH | TASK-009 |
| TASK-011 | [Superadmin Global e Templates de Email](task_011_superadmin_email_templates.md) | COMPLETED | HIGH | TASK-008, TASK-010 |
| TASK-012 | [Auditoria e Versoes para Acoes de Superadmin](task_012_superadmin_audit_versions.md) | COMPLETED | HIGH | TASK-005, TASK-011 |

## Scope

Estas tasks cobrem o Stage 02 definido em `docs/stages/stage_02_auth_rbac.md`: registro, login, refresh token, JWT, selecao de tenant via `X-Tenant-ID` e autorizacao por papel.

## Verification

```bash
docker compose up -d postgres redis qdrant
cd backend
alembic upgrade head
pytest
```

## Notes

- O envio real de email de verificacao ainda nao foi implementado; o registro cria usuario `pending`, conforme contrato, e deixa a integracao de email para uma task dedicada quando houver provider definido.
- O cache Redis de membership descrito na especificacao foi adicionado com TTL de 300s e fallback para PostgreSQL.
- `users.is_superadmin = true` representa o responsavel global da plataforma. Ele acessa qualquer tenant sem precisar de membership, recebe permissao total no RBAC e nao aparece em listagens de membros de tenant.
- A ausencia do superadmin em `memberships` e apenas uma regra de visibilidade/pertencimento. Qualquer acao dele em escopo de tenant deve registrar `tenant_id`, `user_id`, `actor_type = 'superadmin'` e `actor_role = 'superadmin'` em `audit_logs` e, quando houver mutacao versionavel, em `resource_versions`.
- Templates globais de email ficam em `email_templates` e sao gerenciaveis por endpoints de superadmin.
