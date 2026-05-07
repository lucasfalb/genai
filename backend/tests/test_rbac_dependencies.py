from uuid import uuid4

import psycopg
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.rbac import Permission
from app.security import create_access_token
from dependencies.auth import require_permission


async def test_rbac_allows_tenant_admin_and_rejects_viewer(db_connection: psycopg.Connection) -> None:
    suffix = uuid4().hex
    test_app = FastAPI()

    @test_app.get("/protected")
    async def protected(_=Depends(require_permission(Permission.INVITE_MEMBERS))) -> dict[str, bool]:
        return {"ok": True}

    with db_connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tenants (slug, name) VALUES (%s, 'RBAC Tenant') RETURNING id",
            (f"rbac-tenant-{suffix}",),
        )
        tenant_id = cursor.fetchone()[0]
        users = {}
        for role in ("tenant_admin", "viewer"):
            email = f"{role}-{suffix}@example.com"
            cursor.execute(
                """
                INSERT INTO users (email, name, password_hash, status)
                VALUES (%s, %s, 'hash', 'active')
                RETURNING id
                """,
                (email, role),
            )
            user_id = cursor.fetchone()[0]
            users[role] = {"id": user_id, "email": email}
            cursor.execute(
                """
                INSERT INTO memberships (user_id, tenant_id, role, status)
                VALUES (%s, %s, %s, 'active')
                """,
                (user_id, tenant_id, role),
            )
        db_connection.commit()

    admin_token = create_access_token(user_id=users["tenant_admin"]["id"], email=users["tenant_admin"]["email"])
    viewer_token = create_access_token(user_id=users["viewer"]["id"], email=users["viewer"]["email"])

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        admin_response = await client.get(
            "/protected",
            headers={"Authorization": f"Bearer {admin_token}", "X-Tenant-ID": str(tenant_id)},
        )
        viewer_response = await client.get(
            "/protected",
            headers={"Authorization": f"Bearer {viewer_token}", "X-Tenant-ID": str(tenant_id)},
        )

    assert admin_response.status_code == 200
    assert viewer_response.status_code == 403
