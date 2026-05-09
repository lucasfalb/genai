"""TASK-043: Documents upload and status API tests."""
import json
from uuid import uuid4

import psycopg
from httpx import ASGITransport, AsyncClient

from api.v1 import tenant_collections
from app.main import app
from app.object_storage import StoredObject
from app.security import create_access_token
from conftest import api_data


class FakeObjectStorage:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    async def put_object(self, *, key: str, body: bytes, content_type: str) -> StoredObject:
        self.objects[("test-bucket", key)] = body
        return StoredObject(bucket="test-bucket", key=key, etag="etag")

    async def delete_object(self, *, bucket: str, key: str) -> None:
        self.objects.pop((bucket, key), None)


class FakeRedis:
    def __init__(self) -> None:
        self.items: list[tuple[str, str]] = []

    async def rpush(self, key: str, value: str) -> None:
        self.items.append((key, value))


async def test_upload_document_stores_object_and_enqueues_job(
    db_connection: psycopg.Connection,
    monkeypatch,
) -> None:
    setup = _seed_documents_tenant(db_connection)
    storage = FakeObjectStorage()
    redis = FakeRedis()
    monkeypatch.setattr(tenant_collections, "object_storage", storage)
    monkeypatch.setattr(tenant_collections, "redis_client", redis)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/tenant/collections",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"name": "Upload Col"},
        )
        collection_id = api_data(create_resp)["id"]
        upload_resp = await client.post(
            f"/api/v1/tenant/collections/{collection_id}/documents",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            files={"file": ("contract.pdf", b"%PDF-1.4", "application/pdf")},
        )
        collection_resp = await client.get(
            f"/api/v1/tenant/collections/{collection_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    assert upload_resp.status_code == 201
    document = api_data(upload_resp)
    assert document["filename"] == "contract.pdf"
    assert document["status"] == "uploaded"
    assert document["content_type"] == "application/pdf"
    assert document["size_bytes"] == 8
    assert "storage_path" not in document
    assert len(storage.objects) == 1
    object_key = next(iter(storage.objects))[1]
    assert object_key.startswith(f"tenants/{setup['tenant_id']}/collections/{collection_id}/documents/")

    assert len(redis.items) == 1
    assert redis.items[0][0] == "rag:indexing_queue"
    job = json.loads(redis.items[0][1])
    assert job["document_id"] == document["id"]
    assert job["tenant_id"] == str(setup["tenant_id"])
    assert job["collection_id"] == collection_id

    collection = api_data(collection_resp)
    assert collection["indexing_status"] == "indexing"
    assert collection["document_count"] == 1


async def test_list_get_and_delete_document(
    db_connection: psycopg.Connection,
    monkeypatch,
) -> None:
    setup = _seed_documents_tenant(db_connection)
    storage = FakeObjectStorage()
    monkeypatch.setattr(tenant_collections, "object_storage", storage)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/tenant/collections",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"name": "Docs Col"},
        )
        collection_id = api_data(create_resp)["id"]
        upload_resp = await client.post(
            f"/api/v1/tenant/collections/{collection_id}/documents",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
        document_id = api_data(upload_resp)["id"]
        list_resp = await client.get(
            f"/api/v1/tenant/collections/{collection_id}/documents",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )
        get_resp = await client.get(
            f"/api/v1/tenant/collections/{collection_id}/documents/{document_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )
        delete_resp = await client.delete(
            f"/api/v1/tenant/collections/{collection_id}/documents/{document_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )
        get_after_delete = await client.get(
            f"/api/v1/tenant/collections/{collection_id}/documents/{document_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    assert list_resp.status_code == 200
    assert [item["id"] for item in api_data(list_resp)] == [document_id]
    assert get_resp.status_code == 200
    assert api_data(get_resp)["id"] == document_id
    assert delete_resp.status_code == 200
    assert get_after_delete.status_code == 404
    assert storage.objects == {}


async def test_upload_rejects_unsupported_content_type(db_connection: psycopg.Connection) -> None:
    setup = _seed_documents_tenant(db_connection)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/tenant/collections",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"name": "Docs Col"},
        )
        collection_id = api_data(create_resp)["id"]
        upload_resp = await client.post(
            f"/api/v1/tenant/collections/{collection_id}/documents",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            files={"file": ("image.png", b"png", "image/png")},
        )

    assert upload_resp.status_code == 415


async def test_reindex_collection_resets_documents_and_enqueues_jobs(
    db_connection: psycopg.Connection,
    monkeypatch,
) -> None:
    setup = _seed_documents_tenant(db_connection)
    storage = FakeObjectStorage()
    redis = FakeRedis()
    monkeypatch.setattr(tenant_collections, "object_storage", storage)
    monkeypatch.setattr(tenant_collections, "redis_client", redis)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/tenant/collections",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"name": "Reindex Col"},
        )
        collection_id = api_data(create_resp)["id"]
        first_upload = await client.post(
            f"/api/v1/tenant/collections/{collection_id}/documents",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            files={"file": ("one.txt", b"hello", "text/plain")},
        )
        second_upload = await client.post(
            f"/api/v1/tenant/collections/{collection_id}/documents",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            files={"file": ("two.txt", b"world", "text/plain")},
        )
        redis.items.clear()
        reindex_resp = await client.post(
            f"/api/v1/tenant/collections/{collection_id}/reindex",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )
        list_resp = await client.get(
            f"/api/v1/tenant/collections/{collection_id}/documents",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    assert first_upload.status_code == 201
    assert second_upload.status_code == 201
    assert reindex_resp.status_code == 200
    collection = api_data(reindex_resp)
    assert collection["indexing_status"] == "indexing"
    assert collection["indexing_progress"] == 0.0
    assert collection["document_count"] == 2
    assert collection["indexed_count"] == 0
    assert len(redis.items) == 2
    queued_ids = {json.loads(item[1])["document_id"] for item in redis.items}
    assert queued_ids == {api_data(first_upload)["id"], api_data(second_upload)["id"]}
    assert {item["status"] for item in api_data(list_resp)} == {"uploaded"}


async def test_get_missing_document_returns_404(db_connection: psycopg.Connection) -> None:
    setup = _seed_documents_tenant(db_connection)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/tenant/collections",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"name": "Docs Col"},
        )
        collection_id = api_data(create_resp)["id"]
        get_resp = await client.get(
            f"/api/v1/tenant/collections/{collection_id}/documents/{uuid4()}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    assert get_resp.status_code == 404


def _seed_documents_tenant(db_connection: psycopg.Connection) -> dict:
    suffix = uuid4().hex[:8]
    with db_connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tenants (slug, name) VALUES (%s, 'Doc Tenant') RETURNING id",
            (f"doc-tenant-{suffix}",),
        )
        tenant_id = cursor.fetchone()[0]

        email = f"admin-{suffix}@doc.example.com"
        cursor.execute(
            "INSERT INTO users (email, name, password_hash, status) VALUES (%s, 'Admin', 'hash', 'active') RETURNING id",
            (email,),
        )
        user_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO memberships (user_id, tenant_id, role, status) VALUES (%s, %s, 'tenant_admin', 'active')",
            (user_id, tenant_id),
        )
        db_connection.commit()

    return {"tenant_id": tenant_id, "admin_id": user_id, "admin_email": email}
