# Stage 03 Tasks - Registry, Skills, Tools e Vault

| ID | Task | Status | Priority | Depends On |
| :--- | :--- | :--- | :--- | :--- |
| TASK-013 | [Catalogo Global de Skills e Tools](task_013_global_skill_tool_catalog.md) | COMPLETED | CRITICAL | TASK-010 |
| TASK-014 | [Ativacao de Skills e Tools por Instancia](task_014_instance_skill_tool_activation.md) | COMPLETED | CRITICAL | TASK-013 |
| TASK-015 | [Metadata Registry Cache](task_015_metadata_registry_cache.md) | COMPLETED | HIGH | TASK-014 |
| TASK-016 | [Credenciais Tenant-Scoped e Vault Refs](task_016_tool_credentials_vault_refs.md) | COMPLETED | HIGH | TASK-013 |
| TASK-017 | [APIs Registry e Documentacao OpenAPI](task_017_registry_api_openapi.md) | COMPLETED | HIGH | TASK-013, TASK-014, TASK-016 |
| TASK-018 | [Validacao Stage 03](task_018_stage_03_verification.md) | COMPLETED | HIGH | TASK-015, TASK-017 |

## Scope

Estas tasks cobrem o Stage 03 definido em `docs/stages/stage_03_registry.md`: catalogo global de skills/tools, ativacao por instancia, credenciais tenant-scoped como referencias de cofre, cache Redis de metadata e APIs documentadas.

## Verification

```bash
docker compose up -d postgres redis qdrant
cd backend
alembic upgrade head
pytest
cd ..
backend\.venv\Scripts\python scripts\validate_openapi.py
python scripts\validate_tasks.py
```

## Notes

- Credenciais de tools devem persistir referencias (`secret_ref`) e metadata nao sensivel, nunca valores secretos em claro.
- Endpoints tenant-scoped devem exigir `X-Tenant-ID`, RBAC e documentacao OpenAPI suficiente para Swagger.
- Mutacoes tenant-scoped feitas por superadmin continuam registrando ator em audit/version quando aplicavel, sem tornar o superadmin membro visivel do tenant.
