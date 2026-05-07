---
name: endpoint-contract-guardian
description: Validate FastAPI endpoint contracts, Swagger/OpenAPI documentation, and Bruno request coverage for the GenAI project. Use when creating or changing API routes, auth dependencies, request/response schemas, tenant-scoped endpoints, Bruno collections, or task acceptance criteria that mention Swagger/OpenAPI endpoint documentation.
---

# Endpoint Contract Guardian

## Workflow

1. Inspect route files under `backend/api/`.
2. Ensure every route has tags, an explicit summary, a useful description, a response model when data is returned, and documented status codes.
3. For protected endpoints, ensure OpenAPI declares bearer authentication.
4. For tenant-scoped endpoints, ensure `X-Tenant-ID` is required and the route uses tenant context/RBAC dependencies.
5. Create or update the matching Bruno request under `genai-endpoints/` for every created, renamed, or behaviorally changed endpoint.
6. Keep Bruno environment variables in `genai-endpoints/environments/Local.bru` synchronized with any new placeholders used by requests.
7. Run `backend\.venv\Scripts\python scripts\validate_openapi.py` from the repository root after endpoint changes.
8. Fix validation errors before marking API tasks as completed.

## Endpoint Rules

- Public endpoints are limited to healthcheck and auth register/login/refresh unless explicitly documented otherwise.
- JSON success responses must use the shared `ApiResponse[T]` envelope: `{"status":"success","message":null|string,"data":...,"meta":{...}}`.
- JSON error responses must use the shared error envelope from global exception handlers: `{"status":"error","error":{"code":"MACHINE_CODE","message":"Human message"}}`; include `details` only for structured diagnostics such as validation errors.
- Route implementations should return `api_success(...)` for JSON responses and raise `HTTPException` for business errors so handlers preserve the envelope.
- Superadmin endpoints must use `require_superadmin`.
- Tenant endpoints must use `require_permission(...)` or an equivalent dependency that resolves `TenantContext`.
- Do not return secrets, token hashes, credential payloads, or password hashes.
- Use Pydantic response models instead of raw dictionaries for business endpoints.
- Keep route tags stable and domain-oriented, for example `auth`, `superadmin-email-templates`, `registry`, `tenant-registry`.

## Bruno Rules

- The Bruno collection root is `genai-endpoints/`.
- Keep one `.bru` request per API operation, grouped by domain folders such as `Auth`, `Superadmin`, `TenantRegistry`, and `Agent`.
- Rename stale or generic request names when the endpoint purpose is clear; do not leave names such as `teste`.
- Use collection/environment variables instead of hard-coded local values:
  - `{{base_url}}` for the API origin.
  - `{{access_token}}` for Bearer auth.
  - `{{tenant_id}}` for `X-Tenant-ID`.
  - Resource IDs/slugs such as `{{instance_id}}`, `{{session_id}}`, `{{skill_slug}}`, `{{tool_slug}}`, and similar.
- Protected requests must include `auth: bearer` with `token: {{access_token}}`.
- Tenant-scoped requests must include `X-Tenant-ID: {{tenant_id}}`.
- JSON body examples must match the current Pydantic schema and avoid real secrets; use vault references such as `vault://...` for credential examples.
- Streaming endpoints should use the same request contract as the API and be named clearly, for example `Chat SSE`.
- When adding new placeholders to `.bru` files, add them to `genai-endpoints/environments/Local.bru`.

## Validation

Run:

```bash
backend\.venv\Scripts\python scripts\validate_openapi.py
```

This validator imports `backend/app/main.py`, reads the generated OpenAPI schema, and checks route documentation, operation IDs, security, and tenant header requirements.

Also inspect Bruno coverage after endpoint changes:

```bash
rg --files genai-endpoints
rg -n "{{new_placeholder}}" genai-endpoints
```

There is no dedicated Bruno validator yet, so treat missing request files, stale endpoint URLs, hard-coded `localhost`, missing Bearer auth, or missing `X-Tenant-ID` on tenant routes as endpoint contract defects.
