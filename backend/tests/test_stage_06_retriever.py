"""TASK-045: TenantRetriever with RBAC and rag_scope tests."""
from uuid import uuid4, UUID

import psycopg
import pytest

from database.connection import TenantContext, tenant_connection
from database.repositories.collections import CollectionRepository
from rag.retriever import TenantRetriever


class FakeEmbedder:
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeQdrant:
    def __init__(self, return_results: list[dict] | None = None) -> None:
        self.return_results = return_results or []
        self.last_query: dict | None = None

    async def search(self, **kwargs) -> list[dict]:
        self.last_query = kwargs
        return self.return_results


async def test_retrieve_returns_chunks(db_connection: psycopg.Connection) -> None:
    tenant_id = _seed_tenant(db_connection)
    qdrant = FakeQdrant(return_results=[
        {"text": "chunk one", "source": None, "score": 0.95},
        {"text": "chunk two", "source": None, "score": 0.87},
    ])

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        repo = CollectionRepository(conn)
        collection = await repo.create(tenant_id=tenant_id, name="Docs")
        await repo.update_indexing_status(
            tenant_id=tenant_id,
            collection_id=collection.id,
            indexing_status="ready",
            indexed_count=5,
            document_count=5,
        )

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        retriever = TenantRetriever(db=conn, qdrant=qdrant, embedder=FakeEmbedder())
        results = await retriever.retrieve(
            query="test query",
            tenant_id=str(tenant_id),
            rag_scope=[str(collection.id)],
            top_k=5,
        )

    assert len(results) == 2
    assert results[0]["text"] == "chunk one"
    assert results[0]["score"] == 0.95
    assert results[1]["text"] == "chunk two"

    assert qdrant.last_query is not None
    assert qdrant.last_query["tenant_id"] == str(tenant_id)
    assert str(collection.id) in qdrant.last_query["collection_ids"]


async def test_retrieve_empty_rag_scope_returns_empty(db_connection: psycopg.Connection) -> None:
    tenant_id = _seed_tenant(db_connection)
    qdrant = FakeQdrant()

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        retriever = TenantRetriever(db=conn, qdrant=qdrant, embedder=FakeEmbedder())
        results = await retriever.retrieve(
            query="test query",
            tenant_id=str(tenant_id),
            rag_scope=[],
            top_k=5,
        )

    assert results == []
    assert qdrant.last_query is None


async def test_retrieve_no_searchable_collections_returns_empty(
    db_connection: psycopg.Connection,
) -> None:
    tenant_id = _seed_tenant(db_connection)
    qdrant = FakeQdrant()

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        repo = CollectionRepository(conn)
        collection = await repo.create(tenant_id=tenant_id, name="EmptyDocs")
        # collection stays 'empty' — not searchable

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as conn:
        retriever = TenantRetriever(db=conn, qdrant=qdrant, embedder=FakeEmbedder())
        results = await retriever.retrieve(
            query="test query",
            tenant_id=str(tenant_id),
            rag_scope=[str(collection.id)],
            top_k=5,
        )

    assert results == []
    assert qdrant.last_query is None


async def test_retrieve_cross_tenant_isolation(db_connection: psycopg.Connection) -> None:
    tenant_a = _seed_tenant(db_connection)
    tenant_b = _seed_tenant(db_connection)
    qdrant = FakeQdrant(return_results=[
        {"text": "secret chunk", "source": None, "score": 0.9},
    ])

    async with tenant_connection(TenantContext(tenant_id=tenant_a)) as conn:
        repo = CollectionRepository(conn)
        coll_a = await repo.create(tenant_id=tenant_a, name="TenantADocs")
        await repo.update_indexing_status(
            tenant_id=tenant_a,
            collection_id=coll_a.id,
            indexing_status="ready",
            indexed_count=3,
            document_count=3,
        )

    async with tenant_connection(TenantContext(tenant_id=tenant_b)) as conn:
        repo = CollectionRepository(conn)
        coll_b = await repo.create(tenant_id=tenant_b, name="TenantBDocs")
        await repo.update_indexing_status(
            tenant_id=tenant_b,
            collection_id=coll_b.id,
            indexing_status="ready",
            indexed_count=3,
            document_count=3,
        )

    # tenant_a tries to search tenant_b's collection
    async with tenant_connection(TenantContext(tenant_id=tenant_a)) as conn:
        retriever = TenantRetriever(db=conn, qdrant=qdrant, embedder=FakeEmbedder())
        results = await retriever.retrieve(
            query="test",
            tenant_id=str(tenant_a),
            rag_scope=[str(coll_b.id)],
            top_k=5,
        )

    # should get empty because coll_b is not visible from tenant_a's DB
    assert results == []
    assert qdrant.last_query is None


def _seed_tenant(db_connection: psycopg.Connection) -> UUID:
    suffix = uuid4().hex[:8]
    with db_connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tenants (slug, name) VALUES (%s, 'Retriever Tenant') RETURNING id",
            (f"retriever-tenant-{suffix}",),
        )
        tenant_id = cursor.fetchone()[0]
        db_connection.commit()
    return tenant_id
