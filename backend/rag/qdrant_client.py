from uuid import NAMESPACE_URL, uuid5

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from app.config import settings


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
            return
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
            await self.client.upsert(collection_name=self.collection_name, points=points)

    async def delete_document(self, *, document_id: str) -> None:
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
