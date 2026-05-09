import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import text

from app.cache import redis_client
from app.config import settings
from app.object_storage import object_storage
from database.connection import TenantContext, tenant_connection
from database.repositories.collections import CollectionRepository
from database.repositories.documents import DocumentRecord, DocumentRepository
from rag.chunker import chunk_text
from rag.embedder import OpenAIEmbedder
from rag.qdrant_client import QdrantRagClient
from rag.text_extractor import extract_text

INDEXING_QUEUE_KEY = "rag:indexing_queue"


@dataclass(frozen=True)
class IndexingJob:
    tenant_id: UUID
    collection_id: UUID
    document_id: UUID
    action: str = "index"

    @classmethod
    def from_json(cls, payload: str) -> "IndexingJob":
        data = json.loads(payload)
        return cls(
            tenant_id=UUID(data["tenant_id"]),
            collection_id=UUID(data["collection_id"]),
            document_id=UUID(data["document_id"]),
            action=data.get("action", "index"),
        )


class IndexingWorker:
    def __init__(
        self,
        *,
        storage=object_storage,
        embedder: OpenAIEmbedder | None = None,
        qdrant: QdrantRagClient | None = None,
    ) -> None:
        self.storage = storage
        self.embedder = embedder or OpenAIEmbedder()
        self.qdrant = qdrant or QdrantRagClient()

    async def process_payload(self, payload: str) -> None:
        await self.process_job(IndexingJob.from_json(payload))

    async def process_job(self, job: IndexingJob) -> None:
        async with tenant_connection(TenantContext(tenant_id=job.tenant_id)) as connection:
            await connection.execute(
                text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
                {"tenant_id": str(job.tenant_id)},
            )
            document_repo = DocumentRepository(connection)
            collection_repo = CollectionRepository(connection)
            if job.action == "delete":
                await self.qdrant.delete_document(document_id=str(job.document_id))
                await _refresh_collection_status(
                    collection_repo=collection_repo,
                    document_repo=document_repo,
                    tenant_id=job.tenant_id,
                    collection_id=job.collection_id,
                )
                return

            document = await document_repo.get(tenant_id=job.tenant_id, document_id=job.document_id)
            if document is None or document.collection_id != job.collection_id:
                return

            await document_repo.update_status(
                tenant_id=job.tenant_id,
                document_id=job.document_id,
                status="indexing",
            )
            try:
                chunk_count = await self._index_document(job=job, document=document)
                await document_repo.update_status(
                    tenant_id=job.tenant_id,
                    document_id=job.document_id,
                    status="indexed",
                    chunk_count=chunk_count,
                    indexed_at=datetime.now(timezone.utc),
                )
            except Exception as exc:
                await document_repo.update_status(
                    tenant_id=job.tenant_id,
                    document_id=job.document_id,
                    status="failed",
                    error_message=str(exc)[:500],
                )

            await _refresh_collection_status(
                collection_repo=collection_repo,
                document_repo=document_repo,
                tenant_id=job.tenant_id,
                collection_id=job.collection_id,
            )

    async def _index_document(self, *, job: IndexingJob, document: DocumentRecord) -> int:
        if not document.storage_bucket or not document.storage_key:
            raise RuntimeError("Document has no object storage location")
        data = await self.storage.get_object(bucket=document.storage_bucket, key=document.storage_key)
        text = extract_text(filename=document.filename, content_type=document.content_type, data=data)
        chunks = chunk_text(
            text,
            chunk_tokens=settings.rag_chunk_tokens,
            overlap_tokens=settings.rag_chunk_overlap_tokens,
        )
        if not chunks:
            raise RuntimeError("Document produced no indexable text")
        embeddings = await self.embedder.embed_texts(chunks)
        await self.qdrant.delete_document(document_id=str(job.document_id))
        await self.qdrant.upsert_chunks(
            tenant_id=str(job.tenant_id),
            collection_id=str(job.collection_id),
            document_id=str(job.document_id),
            chunks=chunks,
            embeddings=embeddings,
            embedding_model=settings.embedding_model,
        )
        return len(chunks)


async def _refresh_collection_status(
    *,
    collection_repo: CollectionRepository,
    document_repo: DocumentRepository,
    tenant_id: UUID,
    collection_id: UUID,
) -> None:
    stats = await document_repo.recalc_collection_stats(
        tenant_id=tenant_id,
        collection_id=collection_id,
    )
    total = stats["document_count"]
    indexed = stats["indexed_count"]
    failed = stats["failed_count"]
    completed = indexed + failed
    if total == 0:
        status = "empty"
        progress = 0.0
    elif indexed == total:
        status = "ready"
        progress = 1.0
    elif failed == total:
        status = "failed"
        progress = 1.0
    elif completed == total:
        status = "partial"
        progress = 1.0
    else:
        status = "indexing"
        progress = completed / total

    await collection_repo.update_indexing_status(
        tenant_id=tenant_id,
        collection_id=collection_id,
        indexing_status=status,
        indexing_progress=progress,
        document_count=total,
        indexed_count=indexed,
        failed_count=failed,
        last_indexed_at=datetime.now(timezone.utc) if status in {"ready", "partial", "failed"} else None,
    )


async def run_worker(redis: Redis = redis_client) -> None:
    worker = IndexingWorker()
    while True:
        item = await redis.blpop(INDEXING_QUEUE_KEY, timeout=0)
        if item is None:
            continue
        _, payload = item
        await worker.process_payload(payload)


if __name__ == "__main__":
    asyncio.run(run_worker())
