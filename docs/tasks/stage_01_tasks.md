# Stage 01 Tasks - Core DB, Multi-Tenancy e RLS

| ID | Task | Status | Priority | Depends On |
| :--- | :--- | :--- | :--- | :--- |
| TASK-001 | [Core DB Foundation e Migrations](task_001_core_db_foundation.md) | COMPLETED | CRITICAL | - |
| TASK-002 | [Tabelas Globais Core](task_002_global_core_tables.md) | COMPLETED | CRITICAL | TASK-001 |
| TASK-003 | [Schema Tenant-Scoped Completo](task_003_tenant_scoped_schema.md) | COMPLETED | CRITICAL | TASK-001, TASK-002 |
| TASK-004 | [RLS e TenantContext no Banco](task_004_rls_tenant_context.md) | COMPLETED | CRITICAL | TASK-001, TASK-003 |
| TASK-005 | [Sessoes, Mensagens e Auditoria](task_005_sessions_messages_audit.md) | COMPLETED | HIGH | TASK-002, TASK-003, TASK-004 |
| TASK-006 | [Seeds e Verificacao do Core DB](task_006_core_db_seed_and_verification.md) | COMPLETED | HIGH | TASK-001, TASK-002, TASK-003, TASK-004, TASK-005 |

## Scope

Estas tasks cobrem o Stage 01 definido em `docs/stages/stage_01_core_db.md`: PostgreSQL, migrations, schema global, schema tenant-scoped, isolamento por `tenant_id`, RLS, sessoes, mensagens, auditoria e verificacao minima.

## Out of Scope

- Auth, JWT, roles e permissoes de aplicacao.
- CRUDs administrativos e frontend.
- Registry runtime de skills/tools.
- Engine LangGraph, Prompt Runtime, RAG, Hand-off e Channels.
