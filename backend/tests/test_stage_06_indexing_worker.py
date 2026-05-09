"""TASK-044: RAG indexing worker tests."""
from uuid import uuid4

import psycopg

from database.connection import TenantContext, tenant_connection
from database.repositories.collections import CollectionRepository
from database.repositories.documents import DocumentRepository
from rag.indexing_worker import IndexingJob, IndexingWorker


class FakeStorage:
    def __init__(self, objects: dict[tuple[str, str], bytes]) -> None:
        self.objects = objects

    async def get_object(self, *, bucket: str, key: str) -> bytes:
        return self.objects[(bucket, key)]


class FakeEmbedder:
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(index), 0.1, 0.2] for index, _ in enumerate(texts)]


class FakeQdrant:
    def __init__(self) -> None:
        self.upserts: list[dict] = []
        self.deletes: list[str] = []

    async def upsert_chunks(self, **kwargs) -> None:
        self.upserts.append(kwargs)

    async def delete_document(self, *, document_id: str) -> None:
        self.deletes.append(document_id)


async def test_worker_indexes_uploaded_document(db_connection: psycopg.Connection) -> None:
    tenant_id = _seed_tenant(db_connection)
    storage = FakeStorage({("bucket", "doc.txt"): b"hello world " * 80})
    qdrant = FakeQdrant()

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        collection = await CollectionRepository(conn).create(tenant_id=tenant_id, name="Docs")
        document = await DocumentRepository(conn).create(
            tenant_id=tenant_id,
            collection_id=collection.id,
            filename="doc.txt",
            source_type="upload",
            storage_bucket="bucket",
            storage_key="doc.txt",
            content_type="text/plain",
            size_bytes=len(storage.objects[("bucket", "doc.txt")]),
        )

    worker = IndexingWorker(storage=storage, embedder=FakeEmbedder(), qdrant=qdrant)
    await worker.process_job(
        IndexingJob(
            tenant_id=tenant_id,
            collection_id=collection.id,
            document_id=document.id,
        )
    )

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        indexed = await DocumentRepository(conn).get(tenant_id=tenant_id, document_id=document.id)
        updated_collection = await CollectionRepository(conn).get(
            tenant_id=tenant_id,
            collection_id=collection.id,
        )

    assert indexed is not None
    assert indexed.status == "indexed"
    assert indexed.chunk_count > 0
    assert indexed.indexed_at is not None
    assert updated_collection is not None
    assert updated_collection.indexing_status == "ready"
    assert updated_collection.indexing_progress == 1.0
    assert updated_collection.document_count == 1
    assert updated_collection.indexed_count == 1
    assert updated_collection.failed_count == 0
    assert len(qdrant.upserts) == 1
    payload = qdrant.upserts[0]
    assert payload["tenant_id"] == str(tenant_id)
    assert payload["collection_id"] == str(collection.id)
    assert payload["document_id"] == str(document.id)
    assert payload["chunks"]
    assert len(payload["chunks"]) == len(payload["embeddings"])
    assert qdrant.deletes == [str(document.id)]


async def test_worker_marks_document_failed_on_empty_text(
    db_connection: psycopg.Connection,
) -> None:
    tenant_id = _seed_tenant(db_connection)
    storage = FakeStorage({("bucket", "empty.txt"): b"   "})
    qdrant = FakeQdrant()

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        collection = await CollectionRepository(conn).create(tenant_id=tenant_id, name="Docs")
        document = await DocumentRepository(conn).create(
            tenant_id=tenant_id,
            collection_id=collection.id,
            filename="empty.txt",
            source_type="upload",
            storage_bucket="bucket",
            storage_key="empty.txt",
            content_type="text/plain",
            size_bytes=3,
        )

    worker = IndexingWorker(storage=storage, embedder=FakeEmbedder(), qdrant=qdrant)
    await worker.process_job(
        IndexingJob(
            tenant_id=tenant_id,
            collection_id=collection.id,
            document_id=document.id,
        )
    )

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        failed = await DocumentRepository(conn).get(tenant_id=tenant_id, document_id=document.id)
        updated_collection = await CollectionRepository(conn).get(
            tenant_id=tenant_id,
            collection_id=collection.id,
        )

    assert failed is not None
    assert failed.status == "failed"
    assert "no indexable text" in (failed.error_message or "")
    assert updated_collection is not None
    assert updated_collection.indexing_status == "failed"
    assert updated_collection.failed_count == 1
    assert qdrant.upserts == []


async def test_worker_delete_job_removes_qdrant_chunks(
    db_connection: psycopg.Connection,
) -> None:
    tenant_id = _seed_tenant(db_connection)
    qdrant = FakeQdrant()

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        collection = await CollectionRepository(conn).create(tenant_id=tenant_id, name="Docs")
        document = await DocumentRepository(conn).create(
            tenant_id=tenant_id,
            collection_id=collection.id,
            filename="doc.txt",
            source_type="upload",
        )
        await DocumentRepository(conn).delete(tenant_id=tenant_id, document_id=document.id)

    worker = IndexingWorker(storage=FakeStorage({}), embedder=FakeEmbedder(), qdrant=qdrant)
    await worker.process_job(
        IndexingJob(
            tenant_id=tenant_id,
            collection_id=collection.id,
            document_id=document.id,
            action="delete",
        )
    )

    assert qdrant.deletes == [str(document.id)]


def _seed_tenant(db_connection: psycopg.Connection):
    suffix = uuid4().hex[:8]
    with db_connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tenants (slug, name) VALUES (%s, 'Index Tenant') RETURNING id",
            (f"index-tenant-{suffix}",),
        )
        tenant_id = cursor.fetchone()[0]
        db_connection.commit()
    return tenant_id
