"""TASK-042: Collections CRUD API tenant-scoped tests."""
from uuid import uuid4

import psycopg
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.security import create_access_token
from conftest import api_data, api_error


async def test_create_and_list_collections(db_connection: psycopg.Connection) -> None:
    setup = _seed_collections_tenant(db_connection)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/tenant/collections",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"name": "Legal Archive", "description": "All contracts"},
        )
        list_resp = await client.get(
            "/api/v1/tenant/collections",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    assert create_resp.status_code == 201
    created = api_data(create_resp)
    assert created["name"] == "Legal Archive"
    assert created["description"] == "All contracts"
    assert created["indexing_status"] == "empty"
    assert created["indexing_progress"] == 0.0
    assert created["document_count"] == 0
    assert created["indexed_count"] == 0

    assert list_resp.status_code == 200
    ids = {item["id"] for item in api_data(list_resp)}
    assert created["id"] in ids


async def test_get_collection(db_connection: psycopg.Connection) -> None:
    setup = _seed_collections_tenant(db_connection)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/tenant/collections",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"name": "Support KB"},
        )
        collection_id = api_data(create_resp)["id"]
        get_resp = await client.get(
            f"/api/v1/tenant/collections/{collection_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    assert get_resp.status_code == 200
    assert api_data(get_resp)["id"] == collection_id
    assert api_data(get_resp)["name"] == "Support KB"


async def test_get_collection_not_found(db_connection: psycopg.Connection) -> None:
    setup = _seed_collections_tenant(db_connection)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/tenant/collections/{uuid4()}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    assert resp.status_code == 404


async def test_update_collection(db_connection: psycopg.Connection) -> None:
    setup = _seed_collections_tenant(db_connection)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/tenant/collections",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"name": "Old Name"},
        )
        collection_id = api_data(create_resp)["id"]
        patch_resp = await client.patch(
            f"/api/v1/tenant/collections/{collection_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"name": "New Name", "description": "Updated"},
        )

    assert patch_resp.status_code == 200
    updated = api_data(patch_resp)
    assert updated["name"] == "New Name"
    assert updated["description"] == "Updated"


async def test_update_with_no_fields_returns_400(db_connection: psycopg.Connection) -> None:
    setup = _seed_collections_tenant(db_connection)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/tenant/collections",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"name": "Col"},
        )
        collection_id = api_data(create_resp)["id"]
        resp = await client.patch(
            f"/api/v1/tenant/collections/{collection_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={},
        )

    assert resp.status_code == 400


async def test_delete_collection(db_connection: psycopg.Connection) -> None:
    setup = _seed_collections_tenant(db_connection)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/tenant/collections",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"name": "Temp"},
        )
        collection_id = api_data(create_resp)["id"]
        delete_resp = await client.delete(
            f"/api/v1/tenant/collections/{collection_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )
        get_resp = await client.get(
            f"/api/v1/tenant/collections/{collection_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    assert delete_resp.status_code == 200
    assert get_resp.status_code == 404


async def test_delete_cascade_removes_collection_with_indexed_documents(db_connection: psycopg.Connection) -> None:
    setup = _seed_collections_tenant(db_connection)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/tenant/collections",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"name": "Indexed Col"},
        )
        collection_id = api_data(create_resp)["id"]

    _seed_indexed_document(db_connection, setup["tenant_id"], collection_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        delete_resp = await client.delete(
            f"/api/v1/tenant/collections/{collection_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

        assert delete_resp.status_code == 200
        assert "document" in api_data(delete_resp)["message"]

        get_resp = await client.get(
            f"/api/v1/tenant/collections/{collection_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )
        assert get_resp.status_code == 404


async def test_audit_log_on_create_update_delete(db_connection: psycopg.Connection) -> None:
    setup = _seed_collections_tenant(db_connection)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/tenant/collections",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"name": "Audit Col"},
        )
        collection_id = api_data(create_resp)["id"]
        await client.patch(
            f"/api/v1/tenant/collections/{collection_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"name": "Renamed"},
        )
        await client.delete(
            f"/api/v1/tenant/collections/{collection_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    with db_connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(setup["tenant_id"]),))
        cursor.execute(
            "SELECT count(*) FROM audit_logs WHERE tenant_id = %s AND resource = 'collections'",
            (setup["tenant_id"],),
        )
        assert cursor.fetchone()[0] == 3
        cursor.execute("RESET app.current_tenant_id")


async def test_viewer_cannot_mutate_collections(db_connection: psycopg.Connection) -> None:
    setup = _seed_collections_tenant(db_connection)
    viewer_token = create_access_token(user_id=setup["viewer_id"], email=setup["viewer_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/tenant/collections",
            headers={"Authorization": f"Bearer {viewer_token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"name": "Unauthorized"},
        )
        list_resp = await client.get(
            "/api/v1/tenant/collections",
            headers={"Authorization": f"Bearer {viewer_token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    assert create_resp.status_code == 403
    assert list_resp.status_code == 403


async def test_cross_tenant_isolation(db_connection: psycopg.Connection) -> None:
    setup_a = _seed_collections_tenant(db_connection)
    setup_b = _seed_collections_tenant(db_connection)
    token_a = create_access_token(user_id=setup_a["admin_id"], email=setup_a["admin_email"])
    token_b = create_access_token(user_id=setup_b["admin_id"], email=setup_b["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/tenant/collections",
            headers={"Authorization": f"Bearer {token_b}", "X-Tenant-ID": str(setup_b["tenant_id"])},
            json={"name": "Tenant B Collection"},
        )
        col_b_id = api_data(create_resp)["id"]

        get_resp = await client.get(
            f"/api/v1/tenant/collections/{col_b_id}",
            headers={"Authorization": f"Bearer {token_a}", "X-Tenant-ID": str(setup_a["tenant_id"])},
        )
        patch_resp = await client.patch(
            f"/api/v1/tenant/collections/{col_b_id}",
            headers={"Authorization": f"Bearer {token_a}", "X-Tenant-ID": str(setup_a["tenant_id"])},
            json={"name": "Hacked"},
        )
        delete_resp = await client.delete(
            f"/api/v1/tenant/collections/{col_b_id}",
            headers={"Authorization": f"Bearer {token_a}", "X-Tenant-ID": str(setup_a["tenant_id"])},
        )

    assert get_resp.status_code == 404
    assert patch_resp.status_code == 404
    assert delete_resp.status_code == 404


def _seed_collections_tenant(db_connection: psycopg.Connection) -> dict:
    suffix = uuid4().hex[:8]
    with db_connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tenants (slug, name) VALUES (%s, 'Col Tenant') RETURNING id",
            (f"col-tenant-{suffix}",),
        )
        tenant_id = cursor.fetchone()[0]

        users = {}
        for key, role in (("admin", "tenant_admin"), ("viewer", "viewer")):
            email = f"{key}-{suffix}@col.example.com"
            cursor.execute(
                "INSERT INTO users (email, name, password_hash, status) VALUES (%s, %s, 'hash', 'active') RETURNING id",
                (email, key.title()),
            )
            user_id = cursor.fetchone()[0]
            users[key] = {"id": user_id, "email": email}
            cursor.execute(
                "INSERT INTO memberships (user_id, tenant_id, role, status) VALUES (%s, %s, %s, 'active')",
                (user_id, tenant_id, role),
            )

        db_connection.commit()

    return {
        "tenant_id": tenant_id,
        "admin_id": users["admin"]["id"],
        "admin_email": users["admin"]["email"],
        "viewer_id": users["viewer"]["id"],
        "viewer_email": users["viewer"]["email"],
    }


def _seed_indexed_document(
    db_connection: psycopg.Connection,
    tenant_id,
    collection_id: str,
) -> None:
    with db_connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(tenant_id),))
        cursor.execute(
            """
            INSERT INTO documents (tenant_id, collection_id, filename, source_type, status)
            VALUES (%s, %s, 'indexed.pdf', 'upload', 'indexed')
            """,
            (str(tenant_id), collection_id),
        )
        cursor.execute(
            """
            UPDATE collections SET indexed_count = 1, document_count = 1
            WHERE id = %s
            """,
            (collection_id,),
        )
        cursor.execute("RESET app.current_tenant_id")
        db_connection.commit()
