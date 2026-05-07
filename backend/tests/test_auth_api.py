from uuid import uuid4

import psycopg
from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_register_and_login_without_membership_returns_awaiting_assignment() -> None:
    suffix = uuid4().hex
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"pending-{suffix}@example.com",
                "password": "correct-password",
                "name": "Pending User",
            },
        )
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": f"pending-{suffix}@example.com", "password": "correct-password"},
        )

    assert register_response.status_code == 201
    assert register_response.json()["status"] == "pending"
    assert login_response.status_code == 403


async def test_login_with_active_membership_issues_tokens(db_connection: psycopg.Connection) -> None:
    suffix = uuid4().hex
    email = f"member-{suffix}@example.com"
    password = "correct-password"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "name": "Member User"},
        )

    with db_connection.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user_id = cursor.fetchone()[0]
        cursor.execute("UPDATE users SET status = 'active' WHERE id = %s", (user_id,))
        cursor.execute(
            "INSERT INTO tenants (slug, name) VALUES (%s, 'Auth Tenant') RETURNING id",
            (f"auth-tenant-{suffix}",),
        )
        tenant_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO memberships (user_id, tenant_id, role, status)
            VALUES (%s, %s, 'tenant_admin', 'active')
            """,
            (user_id, tenant_id),
        )
        db_connection.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        body = login_response.json()
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": body["refresh_token"]},
        )

    assert login_response.status_code == 200
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["awaiting_assignment"] is False
    assert body["memberships"] == [{"tenant_id": str(tenant_id), "role": "tenant_admin"}]
    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]
