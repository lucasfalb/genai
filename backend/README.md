# Backend Foundation

## Local Services

Start PostgreSQL, Redis and Qdrant:

```bash
docker compose up -d postgres redis qdrant
```

Environment values are kept in the repository root `.env` for local development.

## Migrations

Run from `backend/`:

```bash
alembic upgrade head
alembic downgrade -1
```

## API

Run from `backend/`:

```bash
uvicorn app.main:app --reload
```

Useful endpoints:

- `GET /healthz`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/me/tenants`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/password/forgot`
- `POST /api/v1/auth/password/reset`
- `POST /api/v1/auth/password/change`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/superadmin/email-templates`
- `GET /api/v1/superadmin/email-templates/{slug}`
- `PUT /api/v1/superadmin/email-templates/{slug}`
- `GET /api/v1/superadmin/tenants`
- `POST /api/v1/superadmin/tenants`
- `GET /api/v1/superadmin/tenants/{tenant_id}`
- `PATCH /api/v1/superadmin/tenants/{tenant_id}`
- `GET /api/v1/superadmin/users`
- `GET /api/v1/superadmin/users/{user_id}`
- `PATCH /api/v1/superadmin/users/{user_id}`
- `GET /api/v1/superadmin/registry/skills`
- `PUT /api/v1/superadmin/registry/skills/{slug}`
- `GET /api/v1/superadmin/registry/tools`
- `PUT /api/v1/superadmin/registry/tools/{slug}`
- `GET /api/v1/registry/instances/{instance_id}/metadata`
- `PUT /api/v1/registry/instances/{instance_id}/skills/{skill_slug}`
- `PUT /api/v1/registry/instances/{instance_id}/tools/{tool_slug}`
- `GET /api/v1/registry/credentials`
- `PUT /api/v1/registry/credentials/{skill_slug}`
- `GET /api/v1/tenant/members`
- `PATCH /api/v1/tenant/members/{user_id}`
- `DELETE /api/v1/tenant/members/{user_id}`
- `POST /api/v1/agent/instances/{instance_id}/chat`

JSON endpoints return a standard envelope:

```json
{"status":"success","message":null,"data":{},"meta":{}}
```

Errors use:

```json
{"status":"error","error":{"code":"MACHINE_CODE","message":"Human message"}}
```

`details` is included only when there is structured diagnostic data, such as request validation errors.

## Tests

Run from `backend/`:

```bash
pytest
```

OpenAPI endpoint contract validation from the repository root:

```bash
backend\.venv\Scripts\python scripts\validate_openapi.py
```

## Stage 01 Seed

Run from `backend/`:

```bash
python scripts/seed_stage_01.py
```

## Service URLs

- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- Qdrant HTTP: `http://localhost:6333`
- Qdrant gRPC: `localhost:6334`
