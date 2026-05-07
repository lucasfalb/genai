from uuid import uuid4

import psycopg
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.security import create_access_token
from conftest import api_data, api_error


async def test_superadmin_creates_lists_updates_and_audits_tenant(
    db_connection: psycopg.Connection,
) -> None:
    suffix = uuid4().hex
    superadmin = _seed_superadmin(db_connection, suffix)
    token = create_access_token(user_id=superadmin["id"], email=superadmin["email"], is_superadmin=True)
    tenant_slug = f"managed-tenant-{suffix}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_response = await client.post(
            "/api/v1/superadmin/tenants",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "slug": tenant_slug,
                "name": "Managed Tenant",
                "plan": "starter",
                "settings": {"support_email": "support@example.com"},
            },
        )
        tenant = api_data(create_response)
        list_response = await client.get(
            "/api/v1/superadmin/tenants",
            headers={"Authorization": f"Bearer {token}"},
        )
        get_response = await client.get(
            f"/api/v1/superadmin/tenants/{tenant['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        update_response = await client.patch(
            f"/api/v1/superadmin/tenants/{tenant['id']}",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "suspended", "plan": "growth"},
        )

    assert create_response.status_code == 201
    assert tenant["slug"] == tenant_slug
    assert tenant["status"] == "active"
    assert list_response.status_code == 200
    assert tenant_slug in {item["slug"] for item in api_data(list_response)}
    assert api_data(get_response)["id"] == tenant["id"]
    assert api_data(update_response)["status"] == "suspended"
    assert api_data(update_response)["plan"] == "growth"

    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT count(*)
            FROM audit_logs
            WHERE tenant_id = %s
              AND user_id = %s
              AND actor_type = 'superadmin'
              AND resource = 'tenants'
            """,
            (tenant["id"], superadmin["id"]),
        )
        assert cursor.fetchone()[0] == 2
        cursor.execute(
            "SELECT set_config('app.current_tenant_id', %s, false)",
            (tenant["id"],),
        )
        cursor.execute(
            """
            SELECT count(*)
            FROM resource_versions
            WHERE tenant_id = %s
              AND changed_by = %s
              AND actor_type = 'superadmin'
              AND resource = 'tenants'
            """,
            (tenant["id"], superadmin["id"]),
        )
        assert cursor.fetchone()[0] == 2
        cursor.execute("RESET app.current_tenant_id")


async def test_superadmin_rejects_sensitive_tenant_settings_and_duplicate_slug(
    db_connection: psycopg.Connection,
) -> None:
    suffix = uuid4().hex
    superadmin = _seed_superadmin(db_connection, suffix)
    token = create_access_token(user_id=superadmin["id"], email=superadmin["email"], is_superadmin=True)
    tenant_slug = f"duplicate-tenant-{suffix}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first_response = await client.post(
            "/api/v1/superadmin/tenants",
            headers={"Authorization": f"Bearer {token}"},
            json={"slug": tenant_slug, "name": "Tenant"},
        )
        duplicate_response = await client.post(
            "/api/v1/superadmin/tenants",
            headers={"Authorization": f"Bearer {token}"},
            json={"slug": tenant_slug, "name": "Tenant Again"},
        )
        sensitive_response = await client.post(
            "/api/v1/superadmin/tenants",
            headers={"Authorization": f"Bearer {token}"},
            json={"slug": f"sensitive-{suffix}", "name": "Sensitive", "settings": {"api_key": "plain"}},
        )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert api_error(duplicate_response)["code"] == "TENANT_SLUG_ALREADY_EXISTS"
    assert sensitive_response.status_code == 400


async def test_superadmin_lists_and_updates_users_without_sensitive_fields(
    db_connection: psycopg.Connection,
) -> None:
    suffix = uuid4().hex
    superadmin = _seed_superadmin(db_connection, suffix)
    user = _seed_user(db_connection, suffix)
    token = create_access_token(user_id=superadmin["id"], email=superadmin["email"], is_superadmin=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        list_response = await client.get(
            "/api/v1/superadmin/users",
            params={"q": user["email"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        get_response = await client.get(
            f"/api/v1/superadmin/users/{user['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        update_response = await client.patch(
            f"/api/v1/superadmin/users/{user['id']}",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "active", "is_superadmin": True},
        )

    assert list_response.status_code == 200
    assert [item["id"] for item in api_data(list_response)] == [str(user["id"])]
    assert get_response.status_code == 200
    assert "password" not in str(get_response.json()).lower()
    updated_user = api_data(update_response)
    assert updated_user["status"] == "active"
    assert updated_user["is_superadmin"] is True

    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT count(*)
            FROM audit_logs
            WHERE tenant_id IS NULL
              AND user_id = %s
              AND actor_type = 'superadmin'
              AND action = 'user.updated'
              AND resource_id = %s
            """,
            (superadmin["id"], str(user["id"])),
        )
        assert cursor.fetchone()[0] == 1


async def test_superadmin_admin_endpoints_reject_regular_users_and_self_demote(
    db_connection: psycopg.Connection,
) -> None:
    suffix = uuid4().hex
    superadmin = _seed_superadmin(db_connection, suffix)
    user = _seed_user(db_connection, suffix)
    superadmin_token = create_access_token(user_id=superadmin["id"], email=superadmin["email"], is_superadmin=True)
    user_token = create_access_token(user_id=user["id"], email=user["email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        forbidden_response = await client.get(
            "/api/v1/superadmin/users",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        self_demote_response = await client.patch(
            f"/api/v1/superadmin/users/{superadmin['id']}",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={"is_superadmin": False},
        )
        self_suspend_response = await client.patch(
            f"/api/v1/superadmin/users/{superadmin['id']}",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={"status": "suspended"},
        )

    assert forbidden_response.status_code == 403
    assert self_demote_response.status_code == 400
    assert self_suspend_response.status_code == 400


def _seed_superadmin(db_connection: psycopg.Connection, suffix: str) -> dict:
    email = f"admin-{suffix}@example.com"
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status, is_superadmin)
            VALUES (%s, 'Admin', 'hash', 'active', true)
            RETURNING id
            """,
            (email,),
        )
        user_id = cursor.fetchone()[0]
        db_connection.commit()
    return {"id": user_id, "email": email}


def _seed_user(db_connection: psycopg.Connection, suffix: str) -> dict:
    email = f"user-{suffix}@example.com"
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status)
            VALUES (%s, 'Managed User', 'hash', 'pending')
            RETURNING id
            """,
            (email,),
        )
        user_id = cursor.fetchone()[0]
        db_connection.commit()
    return {"id": user_id, "email": email}
