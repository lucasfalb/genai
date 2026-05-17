import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text

from app.config import settings
from app.object_storage import object_storage
from database.connection import TenantContext, tenant_connection
from database.repositories.collections import CollectionRepository
from database.repositories.documents import DocumentRecord, DocumentRepository
from rag.chunker import chunk_text
from rag.embedder import OpenAIEmbedder
from rag.qdrant_client import QdrantRagClient
from rag.text_extractor import extract_text

logger = logging.getLogger("rag.indexing_worker")


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
        logger.info(
            "Processing job | action=%s tenant=%s collection=%s document=%s",
            job.action, job.tenant_id, job.collection_id, job.document_id,
        )
        async with tenant_connection(TenantContext(tenant_id=job.tenant_id)) as connection:
            await connection.execute(
                text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
                {"tenant_id": str(job.tenant_id)},
            )
            document_repo = DocumentRepository(connection)
            collection_repo = CollectionRepository(connection)
            if job.action == "delete":
                logger.info("Deleting document chunks from Qdrant | document=%s", job.document_id)
                await self.qdrant.delete_document(document_id=str(job.document_id))
                await _refresh_collection_status(
                    collection_repo=collection_repo,
                    document_repo=document_repo,
                    tenant_id=job.tenant_id,
                    collection_id=job.collection_id,
                )
                logger.info("Delete done | document=%s", job.document_id)
                return

            document = await document_repo.get(tenant_id=job.tenant_id, document_id=job.document_id)
            if document is None or document.collection_id != job.collection_id:
                logger.warning(
                    "Document not found or mismatch | tenant=%s document=%s collection=%s",
                    job.tenant_id, job.document_id, job.collection_id,
                )
                return

            logger.info(
                "Indexing document | filename=%s size=%s",
                document.filename, document.size_bytes,
            )
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
                logger.info(
                    "Index complete | document=%s chunks=%d", job.document_id, chunk_count,
                )
            except Exception as exc:
                logger.error(
                    "Index failed | document=%s error=%s", job.document_id, exc, exc_info=True,
                )
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
        logger.info(
            "Fetching from storage | bucket=%s key=%s",
            document.storage_bucket, document.storage_key,
        )
        data = await self.storage.get_object(bucket=document.storage_bucket, key=document.storage_key)
        logger.info("Storage fetched | bytes=%d", len(data))
        extracted = extract_text(filename=document.filename, content_type=document.content_type, data=data)
        logger.info("Text extracted | chars=%d", len(extracted))
        chunks = chunk_text(
            extracted,
            chunk_tokens=settings.rag_chunk_tokens,
            overlap_tokens=settings.rag_chunk_overlap_tokens,
        )
        if not chunks:
            raise RuntimeError("Document produced no indexable text")
        logger.info("Chunking done | chunks=%d", len(chunks))
        embeddings = await self.embedder.embed_texts(chunks)
        logger.info(
            "Embeddings generated | count=%d dim=%d",
            len(embeddings), len(embeddings[0]) if embeddings else 0,
        )
        await self.qdrant.delete_document(document_id=str(job.document_id))
        logger.info("Old chunks deleted from Qdrant | document=%s", job.document_id)
        await self.qdrant.upsert_chunks(
            tenant_id=str(job.tenant_id),
            collection_id=str(job.collection_id),
            document_id=str(job.document_id),
            chunks=chunks,
            embeddings=embeddings,
            embedding_model=settings.embedding_model,
            source=document.filename,
        )
        logger.info(
            "Upsert to Qdrant done | collection=%s points=%d",
            settings.qdrant_collection_name, len(chunks),
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
