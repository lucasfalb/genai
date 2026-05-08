"""TASK-041: Collections and Documents repository tests."""
from uuid import uuid4

import psycopg
import pytest

from database.connection import TenantContext, tenant_connection
from database.repositories.collections import CollectionRepository
from database.repositories.documents import DocumentRepository


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def _seed_tenant(db_connection: psycopg.Connection) -> str:
    slug = f"rag-tenant-{uuid4().hex[:8]}"
    with db_connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tenants (slug, name) VALUES (%s, 'RAG Tenant') RETURNING id",
            (slug,),
        )
        tenant_id = str(cursor.fetchone()[0])
        db_connection.commit()
    return tenant_id


# ---------------------------------------------------------------------------
# CollectionRepository
# ---------------------------------------------------------------------------

async def test_collection_create_and_get(db_connection: psycopg.Connection):
    tenant_id = _seed_tenant(db_connection)

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        repo = CollectionRepository(conn)
        col = await repo.create(tenant_id=tenant_id, name="Legal Docs", description="Contract archive")

    assert col.name == "Legal Docs"
    assert col.description == "Contract archive"
    assert col.indexing_status == "empty"
    assert col.indexing_progress == 0.0
    assert col.document_count == 0
    assert str(col.tenant_id) == tenant_id


async def test_collection_list_by_tenant(db_connection: psycopg.Connection):
    tenant_id = _seed_tenant(db_connection)

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        repo = CollectionRepository(conn)
        await repo.create(tenant_id=tenant_id, name="Col A")
        await repo.create(tenant_id=tenant_id, name="Col B")
        items = await repo.list(tenant_id=tenant_id)

    assert len(items) == 2
    names = {c.name for c in items}
    assert names == {"Col A", "Col B"}


async def test_collection_get_returns_none_for_missing(db_connection: psycopg.Connection):
    tenant_id = _seed_tenant(db_connection)

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        result = await CollectionRepository(conn).get(
            tenant_id=tenant_id, collection_id=uuid4()
        )

    assert result is None


async def test_collection_update_indexing_status(db_connection: psycopg.Connection):
    tenant_id = _seed_tenant(db_connection)

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        repo = CollectionRepository(conn)
        col = await repo.create(tenant_id=tenant_id, name="Docs")
        updated = await repo.update_indexing_status(
            tenant_id=tenant_id,
            collection_id=col.id,
            indexing_status="indexing",
            indexing_progress=0.5,
            document_count=10,
            indexed_count=5,
        )

    assert updated is not None
    assert updated.indexing_status == "indexing"
    assert updated.indexing_progress == 0.5
    assert updated.document_count == 10
    assert updated.indexed_count == 5


async def test_collection_update_status_to_ready(db_connection: psycopg.Connection):
    tenant_id = _seed_tenant(db_connection)

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        repo = CollectionRepository(conn)
        col = await repo.create(tenant_id=tenant_id, name="Docs")
        updated = await repo.update_indexing_status(
            tenant_id=tenant_id,
            collection_id=col.id,
            indexing_status="ready",
            indexing_progress=1.0,
            document_count=3,
            indexed_count=3,
            failed_count=0,
        )

    assert updated.indexing_status == "ready"
    assert updated.indexing_progress == 1.0


async def test_collection_delete(db_connection: psycopg.Connection):
    tenant_id = _seed_tenant(db_connection)

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        repo = CollectionRepository(conn)
        col = await repo.create(tenant_id=tenant_id, name="Temp")
        deleted = await repo.delete(tenant_id=tenant_id, collection_id=col.id)
        after = await repo.get(tenant_id=tenant_id, collection_id=col.id)

    assert deleted is True
    assert after is None


async def test_collection_rls_cross_tenant_isolation(db_connection: psycopg.Connection):
    tenant_a = _seed_tenant(db_connection)
    tenant_b = _seed_tenant(db_connection)

    async with tenant_connection(TenantContext(tenant_id=tenant_a)) as conn:
        col = await CollectionRepository(conn).create(tenant_id=tenant_a, name="Private A")

    async with tenant_connection(TenantContext(tenant_id=tenant_b)) as conn:
        result = await CollectionRepository(conn).get(
            tenant_id=tenant_a, collection_id=col.id
        )

    assert result is None


# ---------------------------------------------------------------------------
# DocumentRepository
# ---------------------------------------------------------------------------

async def test_document_create_and_get(db_connection: psycopg.Connection):
    tenant_id = _seed_tenant(db_connection)

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        col = await CollectionRepository(conn).create(tenant_id=tenant_id, name="Docs")
        doc = await DocumentRepository(conn).create(
            tenant_id=tenant_id,
            collection_id=col.id,
            filename="contract.pdf",
            source_type="upload",
        )

    assert doc.filename == "contract.pdf"
    assert doc.source_type == "upload"
    assert doc.status == "uploaded"
    assert doc.chunk_count == 0
    assert str(doc.collection_id) == str(col.id)


async def test_document_list_by_collection(db_connection: psycopg.Connection):
    tenant_id = _seed_tenant(db_connection)

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        col = await CollectionRepository(conn).create(tenant_id=tenant_id, name="Legal")
        repo = DocumentRepository(conn)
        await repo.create(tenant_id=tenant_id, collection_id=col.id, filename="a.pdf")
        await repo.create(tenant_id=tenant_id, collection_id=col.id, filename="b.pdf")
        docs = await repo.list_by_collection(tenant_id=tenant_id, collection_id=col.id)

    assert len(docs) == 2
    filenames = {d.filename for d in docs}
    assert filenames == {"a.pdf", "b.pdf"}


async def test_document_update_status_indexed(db_connection: psycopg.Connection):
    from datetime import datetime, timezone

    tenant_id = _seed_tenant(db_connection)
    now = datetime.now(timezone.utc)

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        col = await CollectionRepository(conn).create(tenant_id=tenant_id, name="Docs")
        doc = await DocumentRepository(conn).create(
            tenant_id=tenant_id, collection_id=col.id, filename="report.pdf"
        )
        updated = await DocumentRepository(conn).update_status(
            tenant_id=tenant_id,
            document_id=doc.id,
            status="indexed",
            chunk_count=42,
            indexed_at=now,
        )

    assert updated is not None
    assert updated.status == "indexed"
    assert updated.chunk_count == 42
    assert updated.indexed_at is not None


async def test_document_update_status_failed(db_connection: psycopg.Connection):
    tenant_id = _seed_tenant(db_connection)

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        col = await CollectionRepository(conn).create(tenant_id=tenant_id, name="Docs")
        doc = await DocumentRepository(conn).create(
            tenant_id=tenant_id, collection_id=col.id, filename="bad.pdf"
        )
        updated = await DocumentRepository(conn).update_status(
            tenant_id=tenant_id,
            document_id=doc.id,
            status="failed",
            error_message="Unsupported format",
        )

    assert updated.status == "failed"
    assert updated.error_message == "Unsupported format"


async def test_document_cascade_delete_with_collection(db_connection: psycopg.Connection):
    tenant_id = _seed_tenant(db_connection)

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        col_repo = CollectionRepository(conn)
        doc_repo = DocumentRepository(conn)
        col = await col_repo.create(tenant_id=tenant_id, name="Temp")
        doc = await doc_repo.create(
            tenant_id=tenant_id, collection_id=col.id, filename="x.pdf"
        )
        await col_repo.delete(tenant_id=tenant_id, collection_id=col.id)
        result = await doc_repo.get(tenant_id=tenant_id, document_id=doc.id)

    assert result is None
