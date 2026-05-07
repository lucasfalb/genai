from uuid import uuid4

import psycopg
from httpx import ASGITransport, AsyncClient

import api.v1.tenant_members as tenant_members_api
from app.main import app
from app.security import create_access_token
from conftest import api_data, api_error


async def test_tenant_admin_lists_updates_and_removes_members(
    db_connection: psycopg.Connection,
    monkeypatch,
) -> None:
    setup = _seed_members_tenant(db_connection, uuid4().hex)
    fake_redis = _FakeRedis()
    monkeypatch.setattr(tenant_members_api, "redis_client", fake_redis)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        list_response = await client.get(
            "/api/v1/tenant/members",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )
        update_response = await client.patch(
            f"/api/v1/tenant/members/{setup['member_id']}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"role": "viewer", "status": "suspended"},
        )
        remove_response = await client.delete(
            f"/api/v1/tenant/members/{setup['viewer_id']}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )
        after_remove_response = await client.get(
            "/api/v1/tenant/members",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    assert list_response.status_code == 200
    listed_ids = {item["user_id"] for item in api_data(list_response)}
    assert listed_ids == {str(setup["admin_id"]), str(setup["member_id"]), str(setup["viewer_id"])}
    assert str(setup["superadmin_id"]) not in listed_ids
    assert update_response.status_code == 200
    updated = api_data(update_response)
    assert updated["role"] == "viewer"
    assert updated["status"] == "suspended"
    assert remove_response.status_code == 200
    assert str(setup["viewer_id"]) not in {item["user_id"] for item in api_data(after_remove_response)}
    assert f"membership:{setup['member_id']}:{setup['tenant_id']}" in fake_redis.deleted
    assert f"membership:{setup['viewer_id']}:{setup['tenant_id']}" in fake_redis.deleted

    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT set_config('app.current_tenant_id', %s, false)
            """,
            (str(setup["tenant_id"]),),
        )
        cursor.execute(
            """
            SELECT count(*)
            FROM audit_logs
            WHERE tenant_id = %s AND user_id = %s AND resource = 'memberships'
            """,
            (setup["tenant_id"], setup["admin_id"]),
        )
        assert cursor.fetchone()[0] == 2
        cursor.execute(
            """
            SELECT count(*)
            FROM resource_versions
            WHERE tenant_id = %s AND changed_by = %s AND resource = 'memberships'
            """,
            (setup["tenant_id"], setup["admin_id"]),
        )
        assert cursor.fetchone()[0] == 2
        cursor.execute("RESET app.current_tenant_id")


async def test_viewer_cannot_manage_members_and_admin_cannot_modify_self(
    db_connection: psycopg.Connection,
) -> None:
    setup = _seed_members_tenant(db_connection, uuid4().hex)
    viewer_token = create_access_token(user_id=setup["viewer_id"], email=setup["viewer_email"])
    admin_token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        viewer_response = await client.patch(
            f"/api/v1/tenant/members/{setup['member_id']}",
            headers={"Authorization": f"Bearer {viewer_token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"role": "tenant_admin"},
        )
        self_update_response = await client.patch(
            f"/api/v1/tenant/members/{setup['admin_id']}",
            headers={"Authorization": f"Bearer {admin_token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"role": "viewer"},
        )
        self_delete_response = await client.delete(
            f"/api/v1/tenant/members/{setup['admin_id']}",
            headers={"Authorization": f"Bearer {admin_token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    assert viewer_response.status_code == 403
    assert self_update_response.status_code == 400
    assert api_error(self_update_response)["code"] == "TENANT_ADMIN_CANNOT_MODIFY_OWN_MEMBERSHIP"
    assert self_delete_response.status_code == 400


async def test_superadmin_manages_members_without_visible_membership_and_with_actor_context(
    db_connection: psycopg.Connection,
) -> None:
    setup = _seed_members_tenant(db_connection, uuid4().hex)
    token = create_access_token(
        user_id=setup["superadmin_id"],
        email=setup["superadmin_email"],
        is_superadmin=True,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        list_response = await client.get(
            "/api/v1/tenant/members",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )
        update_response = await client.patch(
            f"/api/v1/tenant/members/{setup['member_id']}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"role": "tenant_admin", "status": "active"},
        )

    assert list_response.status_code == 200
    assert str(setup["superadmin_id"]) not in {item["user_id"] for item in api_data(list_response)}
    assert update_response.status_code == 200
    assert api_data(update_response)["role"] == "tenant_admin"

    with db_connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(setup["tenant_id"]),))
        cursor.execute(
            """
            SELECT actor_type, actor_role
            FROM audit_logs
            WHERE tenant_id = %s AND user_id = %s AND resource = 'memberships'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (setup["tenant_id"], setup["superadmin_id"]),
        )
        assert cursor.fetchone() == ("superadmin", "superadmin")
        cursor.execute(
            """
            SELECT actor_type, actor_role
            FROM resource_versions
            WHERE tenant_id = %s AND changed_by = %s AND resource = 'memberships'
            ORDER BY version_no DESC
            LIMIT 1
            """,
            (setup["tenant_id"], setup["superadmin_id"]),
        )
        assert cursor.fetchone() == ("superadmin", "superadmin")
        cursor.execute("RESET app.current_tenant_id")


def _seed_members_tenant(db_connection: psycopg.Connection, suffix: str) -> dict:
    with db_connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tenants (slug, name) VALUES (%s, 'Members Tenant') RETURNING id",
            (f"members-tenant-{suffix}",),
        )
        tenant_id = cursor.fetchone()[0]
        users = {}
        for key, role in (("admin", "tenant_admin"), ("member", "member"), ("viewer", "viewer")):
            email = f"{key}-{suffix}@example.com"
            cursor.execute(
                """
                INSERT INTO users (email, name, password_hash, status)
                VALUES (%s, %s, 'hash', 'active')
                RETURNING id
                """,
                (email, key.title()),
            )
            user_id = cursor.fetchone()[0]
            users[key] = {"id": user_id, "email": email}
            cursor.execute(
                """
                INSERT INTO memberships (user_id, tenant_id, role, status)
                VALUES (%s, %s, %s, 'active')
                """,
                (user_id, tenant_id, role),
            )
        superadmin_email = f"superadmin-{suffix}@example.com"
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status, is_superadmin)
            VALUES (%s, 'Superadmin', 'hash', 'active', true)
            RETURNING id
            """,
            (superadmin_email,),
        )
        superadmin_id = cursor.fetchone()[0]
        db_connection.commit()
    return {
        "tenant_id": tenant_id,
        "admin_id": users["admin"]["id"],
        "admin_email": users["admin"]["email"],
        "member_id": users["member"]["id"],
        "member_email": users["member"]["email"],
        "viewer_id": users["viewer"]["id"],
        "viewer_email": users["viewer"]["email"],
        "superadmin_id": superadmin_id,
        "superadmin_email": superadmin_email,
    }


class _FakeRedis:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def delete(self, key: str) -> None:
        self.deleted.append(key)
