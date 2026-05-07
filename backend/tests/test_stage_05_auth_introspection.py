from uuid import uuid4

import psycopg
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.security import create_access_token, hash_password
from conftest import api_data


async def test_me_returns_safe_profile_for_pending_user(db_connection: psycopg.Connection) -> None:
    suffix = uuid4().hex
    email = f"pending-me-{suffix}@example.com"

    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status)
            VALUES (%s, 'Pending Me', 'hash', 'pending')
            RETURNING id
            """,
            (email,),
        )
        user_id = cursor.fetchone()[0]
        db_connection.commit()

    token = create_access_token(user_id=user_id, email=email)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = api_data(response)
    assert body == {
        "id": str(user_id),
        "email": email,
        "name": "Pending Me",
        "status": "pending",
        "is_superadmin": False,
    }
    assert "password_hash" not in str(response.json())


async def test_me_tenants_returns_real_memberships_and_superadmin_empty(
    db_connection: psycopg.Connection,
) -> None:
    suffix = uuid4().hex
    member = _seed_member(db_connection, suffix)
    superadmin = _seed_superadmin(db_connection, suffix)
    member_token = create_access_token(user_id=member["user_id"], email=member["email"])
    superadmin_token = create_access_token(
        user_id=superadmin["user_id"],
        email=superadmin["email"],
        is_superadmin=True,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        member_response = await client.get(
            "/api/v1/auth/me/tenants",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        superadmin_response = await client.get(
            "/api/v1/auth/me/tenants",
            headers={"Authorization": f"Bearer {superadmin_token}"},
        )
        superadmin_me_response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {superadmin_token}"},
        )

    assert member_response.status_code == 200
    assert api_data(member_response) == [
        {
            "tenant_id": str(member["tenant_id"]),
            "tenant_slug": member["tenant_slug"],
            "tenant_name": "Introspection Tenant",
            "role": "tenant_admin",
            "status": "active",
        }
    ]
    assert superadmin_response.status_code == 200
    assert api_data(superadmin_response) == []
    assert api_data(superadmin_me_response)["is_superadmin"] is True


async def test_logout_revokes_refresh_token_for_authenticated_user(
    db_connection: psycopg.Connection,
) -> None:
    suffix = uuid4().hex
    password = "correct-password"
    user = _seed_member(db_connection, suffix, password=password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": user["email"], "password": password},
        )
        tokens = api_data(login_response)
        logout_response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={"refresh_token": tokens["refresh_token"]},
        )
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )

    assert logout_response.status_code == 200
    assert api_data(logout_response)["message"] == "Logged out successfully."
    assert refresh_response.status_code == 401


async def test_logout_without_refresh_token_revokes_all_user_refresh_tokens(
    db_connection: psycopg.Connection,
) -> None:
    suffix = uuid4().hex
    password = "correct-password"
    user = _seed_member(db_connection, suffix, password=password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first_login = await client.post("/api/v1/auth/login", json={"email": user["email"], "password": password})
        second_login = await client.post("/api/v1/auth/login", json={"email": user["email"], "password": password})
        first_tokens = api_data(first_login)
        second_tokens = api_data(second_login)
        logout_response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {first_tokens['access_token']}"},
            json={},
        )
        first_refresh = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": first_tokens["refresh_token"]},
        )
        second_refresh = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": second_tokens["refresh_token"]},
        )

    assert logout_response.status_code == 200
    assert first_refresh.status_code == 401
    assert second_refresh.status_code == 401


def _seed_member(db_connection: psycopg.Connection, suffix: str, *, password: str = "hash") -> dict:
    email = f"member-me-{suffix}@example.com"
    tenant_slug = f"introspection-tenant-{suffix}"
    with db_connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tenants (slug, name) VALUES (%s, 'Introspection Tenant') RETURNING id",
            (tenant_slug,),
        )
        tenant_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status)
            VALUES (%s, 'Member Me', %s, 'active')
            RETURNING id
            """,
            (email, hash_password(password) if password != "hash" else "hash"),
        )
        user_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO memberships (user_id, tenant_id, role, status)
            VALUES (%s, %s, 'tenant_admin', 'active')
            """,
            (user_id, tenant_id),
        )
        db_connection.commit()
    return {"user_id": user_id, "email": email, "tenant_id": tenant_id, "tenant_slug": tenant_slug}


def _seed_superadmin(db_connection: psycopg.Connection, suffix: str) -> dict:
    email = f"superadmin-me-{suffix}@example.com"
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status, is_superadmin)
            VALUES (%s, 'Superadmin Me', 'hash', 'active', true)
            RETURNING id
            """,
            (email,),
        )
        user_id = cursor.fetchone()[0]
        db_connection.commit()
    return {"user_id": user_id, "email": email}
