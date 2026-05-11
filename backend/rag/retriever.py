import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncConnection

from app.config import settings
from database.repositories.collections import CollectionRepository
from rag.embedder import OpenAIEmbedder
from rag.qdrant_client import QdrantRagClient

logger = logging.getLogger("rag.retriever")


class TenantRetriever:
    def __init__(
        self,
        *,
        db: AsyncConnection,
        qdrant: QdrantRagClient | None = None,
        embedder: OpenAIEmbedder | None = None,
    ) -> None:
        self.db = db
        self.qdrant = qdrant or QdrantRagClient()
        self.embedder = embedder or OpenAIEmbedder()

    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        rag_scope: list[str],
        top_k: int | None = None,
        score_threshold: float | None = None,
    ) -> list[dict]:
        if not rag_scope:
            logger.debug("Retrieve skipped: rag_scope is empty | tenant=%s", tenant_id)
            return []

        effective_top_k = top_k if top_k is not None else settings.rag_top_k
        effective_threshold = (
            score_threshold if score_threshold is not None else settings.rag_score_threshold
        )

        repo = CollectionRepository(self.db)
        ready_scope = await repo.get_searchable_collections(
            tenant_id=UUID(tenant_id),
            collection_ids=[UUID(cid) for cid in rag_scope],
            allowed_statuses=["ready", "partial", "indexing"],
        )
        if not ready_scope:
            logger.debug("Retrieve skipped: no searchable collections | tenant=%s", tenant_id)
            return []

        ready_ids = [str(cid) for cid in ready_scope]
        logger.debug(
            "Retrieving chunks | tenant=%s collections=%s top_k=%d threshold=%.2f",
            tenant_id, ready_ids, effective_top_k, effective_threshold,
        )

        embedding = (await self.embedder.embed_texts([query]))[0]

        raw_results = await self.qdrant.search(
            query_vector=embedding,
            tenant_id=tenant_id,
            collection_ids=ready_ids,
            document_status="indexed",
            top_k=min(effective_top_k, 20),
        )

        results = [
            chunk for chunk in raw_results
            if (chunk.get("score") or 0.0) >= effective_threshold
        ]
        logger.debug(
            "Retrieved %d chunks (%d above threshold %.2f) | tenant=%s",
            len(raw_results), len(results), effective_threshold, tenant_id,
        )
        return results
