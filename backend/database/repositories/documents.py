from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


@dataclass(frozen=True)
class DocumentRecord:
    id: UUID
    tenant_id: UUID
    collection_id: UUID
    filename: str
    source_type: str
    status: str
    chunk_count: int
    error_message: str | None
    storage_bucket: str | None
    storage_key: str | None
    content_type: str | None
    size_bytes: int | None
    created_at: datetime
    indexed_at: datetime | None


class DocumentRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def create(
        self,
        *,
        tenant_id: UUID,
        collection_id: UUID,
        filename: str,
        document_id: UUID | None = None,
        source_type: str = "upload",
        storage_bucket: str | None = None,
        storage_key: str | None = None,
        content_type: str | None = None,
        size_bytes: int | None = None,
    ) -> DocumentRecord:
        result = await self.connection.execute(
            text(
                """
                INSERT INTO documents (id, tenant_id, collection_id, filename, source_type,
                                       storage_bucket, storage_key, content_type, size_bytes)
                VALUES (COALESCE(CAST(:document_id AS uuid), gen_random_uuid()), :tenant_id, :collection_id,
                        :filename, :source_type, :storage_bucket, :storage_key,
                        :content_type, :size_bytes)
                RETURNING id, tenant_id, collection_id, filename, source_type,
                          status, chunk_count, error_message, storage_bucket, storage_key,
                          content_type, size_bytes, created_at, indexed_at
                """
            ),
            {
                "document_id": document_id,
                "tenant_id": tenant_id,
                "collection_id": collection_id,
                "filename": filename,
                "source_type": source_type,
                "storage_bucket": storage_bucket,
                "storage_key": storage_key,
                "content_type": content_type,
                "size_bytes": size_bytes,
            },
        )
        return _from_row(result.one())

    async def list_by_collection(
        self,
        *,
        tenant_id: UUID,
        collection_id: UUID,
    ) -> list[DocumentRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT id, tenant_id, collection_id, filename, source_type,
                       status, chunk_count, error_message, storage_bucket, storage_key,
                       content_type, size_bytes, created_at, indexed_at
                FROM documents
                WHERE tenant_id = :tenant_id
                  AND tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                  AND collection_id = :collection_id
                ORDER BY created_at DESC
                """
            ),
            {"tenant_id": tenant_id, "collection_id": collection_id},
        )
        return [_from_row(row) for row in result.fetchall()]

    async def reset_collection_for_reindex(
        self,
        *,
        tenant_id: UUID,
        collection_id: UUID,
    ) -> list[DocumentRecord]:
        result = await self.connection.execute(
            text(
                """
                UPDATE documents
                SET status        = 'uploaded',
                    chunk_count   = 0,
                    error_message = NULL,
                    indexed_at    = NULL
                WHERE tenant_id = :tenant_id
                  AND tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                  AND collection_id = :collection_id
                RETURNING id, tenant_id, collection_id, filename, source_type,
                          status, chunk_count, error_message, storage_bucket, storage_key,
                          content_type, size_bytes, created_at, indexed_at
                """
            ),
            {"tenant_id": tenant_id, "collection_id": collection_id},
        )
        return [_from_row(row) for row in result.fetchall()]

    async def get(self, *, tenant_id: UUID, document_id: UUID) -> DocumentRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT id, tenant_id, collection_id, filename, source_type,
                       status, chunk_count, error_message, storage_bucket, storage_key,
                       content_type, size_bytes, created_at, indexed_at
                FROM documents
                WHERE tenant_id = :tenant_id
                  AND tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                  AND id = :document_id
                """
            ),
            {"tenant_id": tenant_id, "document_id": document_id},
        )
        row = result.one_or_none()
        return _from_row(row) if row else None

    async def update_status(
        self,
        *,
        tenant_id: UUID,
        document_id: UUID,
        status: str,
        chunk_count: int | None = None,
        error_message: str | None = None,
        indexed_at: datetime | None = None,
    ) -> DocumentRecord | None:
        result = await self.connection.execute(
            text(
                """
                UPDATE documents
                SET status        = :status,
                    chunk_count   = COALESCE(:chunk_count, chunk_count),
                    error_message = COALESCE(:error_message, error_message),
                    indexed_at    = COALESCE(:indexed_at, indexed_at)
                WHERE tenant_id = :tenant_id
                  AND tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                  AND id = :document_id
                RETURNING id, tenant_id, collection_id, filename, source_type,
                          status, chunk_count, error_message, storage_bucket, storage_key,
                          content_type, size_bytes, created_at, indexed_at
                """
            ),
            {
                "tenant_id": tenant_id,
                "document_id": document_id,
                "status": status,
                "chunk_count": chunk_count,
                "error_message": error_message,
                "indexed_at": indexed_at,
            },
        )
        row = result.one_or_none()
        return _from_row(row) if row else None

    async def delete(self, *, tenant_id: UUID, document_id: UUID) -> bool:
        result = await self.connection.execute(
            text(
                """
                DELETE FROM documents
                WHERE tenant_id = :tenant_id
                  AND tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                  AND id = :document_id
                """
            ),
            {"tenant_id": tenant_id, "document_id": document_id},
        )
        return result.rowcount > 0

    async def recalc_collection_stats(
        self,
        *,
        tenant_id: UUID,
        collection_id: UUID,
    ) -> dict:
        result = await self.connection.execute(
            text(
                """
                SELECT
                  COUNT(*) AS total,
                  COUNT(*) FILTER (WHERE status = 'indexed') AS indexed,
                  COUNT(*) FILTER (WHERE status = 'failed') AS failed
                FROM documents
                WHERE tenant_id = :tenant_id
                  AND tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                  AND collection_id = :collection_id
                """
            ),
            {"tenant_id": tenant_id, "collection_id": collection_id},
        )
        row = result.one()
        return {
            "document_count": row.total,
            "indexed_count": row.indexed,
            "failed_count": row.failed,
        }


def _from_row(row) -> DocumentRecord:
    return DocumentRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        collection_id=row.collection_id,
        filename=row.filename,
        source_type=row.source_type,
        status=row.status,
        chunk_count=row.chunk_count,
        error_message=row.error_message,
        storage_bucket=row.storage_bucket,
        storage_key=row.storage_key,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        created_at=row.created_at,
        indexed_at=row.indexed_at,
    )
