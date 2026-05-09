import logging
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from app.config import settings

logger = logging.getLogger("rag.qdrant_client")


class QdrantRagClient:
    def __init__(
        self,
        *,
        url: str | None = None,
        collection_name: str | None = None,
        vector_size: int | None = None,
    ) -> None:
        self.client = AsyncQdrantClient(url=url or settings.qdrant_url)
        self.collection_name = collection_name or settings.qdrant_collection_name
        self.vector_size = vector_size or settings.embedding_dimension

    async def ensure_collection(self) -> None:
        exists = await self.client.collection_exists(self.collection_name)
        if exists:
            logger.debug("Collection exists | collection=%s", self.collection_name)
            return
        logger.info("Creating Qdrant collection | name=%s dim=%d", self.collection_name, self.vector_size)
        await self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.vector_size,
                distance=models.Distance.COSINE,
            ),
        )

    async def upsert_chunks(
        self,
        *,
        tenant_id: str,
        collection_id: str,
        document_id: str,
        chunks: list[str],
        embeddings: list[list[float]],
        embedding_model: str,
    ) -> None:
        await self.ensure_collection()
        points = [
            models.PointStruct(
                id=str(uuid5(NAMESPACE_URL, f"{document_id}:{index}")),
                vector=embedding,
                payload={
                    "tenant_id": tenant_id,
                    "collection_id": collection_id,
                    "document_id": document_id,
                    "document_status": "indexed",
                    "chunk_index": index,
                    "embedding_model": embedding_model,
                    "text": chunk,
                },
            )
            for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
        ]
        if points:
            logger.info(
                "Upserting %d points to Qdrant | collection=%s tenant=%s document=%s",
                len(points), self.collection_name, tenant_id, document_id,
            )
            await self.client.upsert(collection_name=self.collection_name, points=points)

    async def search(
        self,
        *,
        query_vector: list[float],
        tenant_id: str,
        collection_ids: list[str],
        document_status: str = "indexed",
        top_k: int = 5,
    ) -> list[dict]:
        await self.ensure_collection()
        results = await self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(key="tenant_id", match=models.MatchValue(value=tenant_id)),
                    models.FieldCondition(key="collection_id", match=models.MatchAny(any=collection_ids)),
                    models.FieldCondition(key="document_status", match=models.MatchValue(value=document_status)),
                ]
            ),
            limit=top_k,
        )
        return [
            {"text": r.payload.get("text", ""), "source": r.payload.get("source"), "score": r.score}
            for r in results
        ]

    async def delete_document(self, *, document_id: str) -> None:
        logger.info("Deleting Qdrant points | document=%s", document_id)
        await self.ensure_collection()
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )
