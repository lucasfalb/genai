import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncConnection

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
        top_k: int = 5,
    ) -> list[dict]:
        if not rag_scope:
            logger.debug("Retrieve skipped: rag_scope is empty | tenant=%s", tenant_id)
            return []

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
            "Retrieving chunks | tenant=%s collections=%s top_k=%d",
            tenant_id, ready_ids, top_k,
        )

        embedding = (await self.embedder.embed_texts([query]))[0]

        results = await self.qdrant.search(
            query_vector=embedding,
            tenant_id=tenant_id,
            collection_ids=ready_ids,
            document_status="indexed",
            top_k=min(top_k, 20),
        )

        logger.debug("Retrieved %d chunks | tenant=%s", len(results), tenant_id)
        return results
