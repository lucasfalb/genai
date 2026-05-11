import logging
from uuid import UUID

from sqlalchemy import text
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
        self.last_usage: dict = {"prompt_tokens": 0, "total_tokens": 0}

    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        rag_scope: list[str],
        top_k: int | None = None,
        score_threshold: float | None = None,
    ) -> list[dict]:
        self.last_usage = {"prompt_tokens": 0, "total_tokens": 0}
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

        if hasattr(self.embedder, "embed_texts_with_usage"):
            embed_result = await self.embedder.embed_texts_with_usage([query])
            self.last_usage = {
                "prompt_tokens": embed_result.prompt_tokens,
                "total_tokens": embed_result.total_tokens,
            }
            embedding = embed_result.embeddings[0]
        else:
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

        missing_source_ids = {
            chunk.get("document_id")
            for chunk in results
            if not chunk.get("source") and chunk.get("document_id")
        }
        if missing_source_ids:
            filename_map = await self._fetch_filenames(
                tenant_id=tenant_id, document_ids=missing_source_ids
            )
            for chunk in results:
                if not chunk.get("source") and chunk.get("document_id"):
                    chunk["source"] = filename_map.get(chunk["document_id"])

        logger.info(
            "Retrieved %d/%d chunks (threshold %.2f) | tenant=%s top_score=%s",
            len(results),
            len(raw_results),
            effective_threshold,
            tenant_id,
            f"{max((c.get('score') or 0.0) for c in raw_results):.3f}" if raw_results else "n/a",
        )
        return results

    async def _fetch_filenames(self, *, tenant_id: str, document_ids: set[str]) -> dict[str, str]:
        if not document_ids:
            return {}
        result = await self.db.execute(
            text(
                """
                SELECT id::text AS id, filename
                FROM documents
                WHERE tenant_id = :tenant_id AND id = ANY(CAST(:ids AS uuid[]))
                """
            ),
            {"tenant_id": UUID(tenant_id), "ids": list(document_ids)},
        )
        return {row.id: row.filename for row in result.fetchall()}
