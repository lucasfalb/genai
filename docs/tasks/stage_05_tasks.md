# Stage 05 Tasks - Base Multitenant Workflows

| ID | Task | Status | Priority | Depends On |
| :--- | :--- | :--- | :--- | :--- |
| TASK-025 | [Auth Token Tables e Email Event Outbox](task_025_auth_token_tables_email_event_outbox.md) | COMPLETED | CRITICAL | TASK-011 |
| TASK-026 | [Account Activation Flow](task_026_account_activation_flow.md) | COMPLETED | CRITICAL | TASK-025 |
| TASK-027 | [Password Recovery e Change Flow](task_027_password_recovery_change_flow.md) | PENDING | CRITICAL | TASK-025 |
| TASK-028 | [Auth Me Logout e Session Introspection](task_028_auth_me_logout_session_introspection.md) | PENDING | HIGH | TASK-008 |
| TASK-029 | [Superadmin Tenant e User Administration](task_029_superadmin_tenant_user_administration.md) | PENDING | CRITICAL | TASK-012 |
| TASK-030 | [Tenant Members e RBAC Administration](task_030_tenant_members_rbac_administration.md) | PENDING | CRITICAL | TASK-010, TASK-012 |
| TASK-031 | [Tenant Invitation Lifecycle](task_031_tenant_invitation_lifecycle.md) | PENDING | CRITICAL | TASK-025, TASK-030 |
| TASK-032 | [Tenant Agent Instance CRUD](task_032_tenant_agent_instance_crud.md) | PENDING | CRITICAL | TASK-015, TASK-030 |
| TASK-033 | [Workflow Audit Versions e Cache Invalidation](task_033_workflow_audit_versions_cache_invalidation.md) | PENDING | HIGH | TASK-029, TASK-030, TASK-031, TASK-032 |
| TASK-034 | [Stage 05 API Bruno e Workflow Verification](task_034_stage_05_api_bruno_workflow_verification.md) | PENDING | HIGH | TASK-026, TASK-027, TASK-028, TASK-029, TASK-030, TASK-031, TASK-032, TASK-033 |

## Scope

Estas tasks cobrem o Stage 05 definido em `docs/stages/stage_05_base_multitenant_workflows.md`: completar os workflows base de autenticacao, tenants, membros, convites, instancias, auditoria/versionamento e contratos Bruno/OpenAPI.

## Implementation Order

1. Criar tabelas auxiliares de tokens transacionais e email outbox.
2. Fechar account activation e password lifecycle.
3. Expor introspeccao de auth e logout.
4. Implementar administracao superadmin de tenants/users.
5. Implementar members/RBAC e invitations por tenant.
6. Implementar CRUD tenant-scoped de instancias.
7. Garantir audit/version/cache para todas as mutacoes.
8. Validar OpenAPI, Bruno e testes end-to-end.

## Notes

- Superadmin controla qualquer tenant sem membership visivel.
- Listagem de membros deve consultar `memberships` e excluir `users.is_superadmin = true`.
- Toda rota tenant-scoped exige Bearer token, `X-Tenant-ID` e RBAC.
- Toda rota criada neste stage deve ganhar request correspondente em `genai-endpoints/`.
