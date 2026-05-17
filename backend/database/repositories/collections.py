from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


@dataclass(frozen=True)
class CollectionRecord:
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    indexing_status: str
    indexing_progress: float
    document_count: int
    indexed_count: int
    failed_count: int
    last_indexed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CollectionRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def create(
        self,
        *,
        tenant_id: UUID,
        name: str,
        description: str | None = None,
    ) -> CollectionRecord:
        result = await self.connection.execute(
            text(
                """
                INSERT INTO collections (tenant_id, name, description)
                VALUES (:tenant_id, :name, :description)
                RETURNING id, tenant_id, name, description,
                          indexing_status, indexing_progress,
                          document_count, indexed_count, failed_count,
                          last_indexed_at, created_at, updated_at
                """
            ),
            {"tenant_id": tenant_id, "name": name, "description": description},
        )
        return _from_row(result.one())

    async def list(self, *, tenant_id: UUID) -> list[CollectionRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT id, tenant_id, name, description,
                       indexing_status, indexing_progress,
                       document_count, indexed_count, failed_count,
                       last_indexed_at, created_at, updated_at
                FROM collections
                WHERE tenant_id = :tenant_id
                  AND tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                ORDER BY created_at DESC
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [_from_row(row) for row in result.fetchall()]

    async def get(self, *, tenant_id: UUID, collection_id: UUID) -> CollectionRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT id, tenant_id, name, description,
                       indexing_status, indexing_progress,
                       document_count, indexed_count, failed_count,
                       last_indexed_at, created_at, updated_at
                FROM collections
                WHERE tenant_id = :tenant_id
                  AND tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                  AND id = :collection_id
                """
            ),
            {"tenant_id": tenant_id, "collection_id": collection_id},
        )
        row = result.one_or_none()
        return _from_row(row) if row else None

    async def update_indexing_status(
        self,
        *,
        tenant_id: UUID,
        collection_id: UUID,
        indexing_status: str | None = None,
        indexing_progress: float | None = None,
        document_count: int | None = None,
        indexed_count: int | None = None,
        failed_count: int | None = None,
        last_indexed_at: datetime | None = None,
    ) -> CollectionRecord | None:
        result = await self.connection.execute(
            text(
                """
                UPDATE collections
                SET indexing_status   = COALESCE(:indexing_status, indexing_status),
                    indexing_progress = COALESCE(:indexing_progress, indexing_progress),
                    document_count    = COALESCE(:document_count, document_count),
                    indexed_count     = COALESCE(:indexed_count, indexed_count),
                    failed_count      = COALESCE(:failed_count, failed_count),
                    last_indexed_at   = COALESCE(:last_indexed_at, last_indexed_at),
                    updated_at        = now()
                WHERE tenant_id = :tenant_id
                  AND tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                  AND id = :collection_id
                RETURNING id, tenant_id, name, description,
                          indexing_status, indexing_progress,
                          document_count, indexed_count, failed_count,
                          last_indexed_at, created_at, updated_at
                """
            ),
            {
                "tenant_id": tenant_id,
                "collection_id": collection_id,
                "indexing_status": indexing_status,
                "indexing_progress": indexing_progress,
                "document_count": document_count,
                "indexed_count": indexed_count,
                "failed_count": failed_count,
                "last_indexed_at": last_indexed_at,
            },
        )
        row = result.one_or_none()
        return _from_row(row) if row else None

    async def update_metadata(
        self,
        *,
        tenant_id: UUID,
        collection_id: UUID,
        name: str | None = None,
        description: str | None = None,
    ) -> "CollectionRecord | None":
        result = await self.connection.execute(
            text(
                """
                UPDATE collections
                SET name        = COALESCE(:name, name),
                    description = COALESCE(:description, description),
                    updated_at  = now()
                WHERE tenant_id = :tenant_id
                  AND tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                  AND id = :collection_id
                RETURNING id, tenant_id, name, description,
                          indexing_status, indexing_progress,
                          document_count, indexed_count, failed_count,
                          last_indexed_at, created_at, updated_at
                """
            ),
            {
                "tenant_id": tenant_id,
                "collection_id": collection_id,
                "name": name,
                "description": description,
            },
        )
        row = result.one_or_none()
        return _from_row(row) if row else None

    async def get_searchable_collections(
        self,
        *,
        tenant_id: UUID,
        collection_ids: list[UUID],
        allowed_statuses: list[str],
    ) -> list[UUID]:
        if not collection_ids:
            return []
        result = await self.connection.execute(
            text(
                """
                SELECT id FROM collections
                WHERE tenant_id = :tenant_id
                  AND tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                  AND id = ANY(:collection_ids)
                  AND indexing_status = ANY(:allowed_statuses)
                """
            ),
            {
                "tenant_id": tenant_id,
                "collection_ids": collection_ids,
                "allowed_statuses": allowed_statuses,
            },
        )
        return [row.id for row in result.fetchall()]

    async def delete(self, *, tenant_id: UUID, collection_id: UUID) -> bool:
        await self.connection.execute(
            text(
                """
                DELETE FROM documents
                WHERE tenant_id = :tenant_id
                  AND tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                  AND collection_id = :collection_id
                """
            ),
            {"tenant_id": tenant_id, "collection_id": collection_id},
        )
        result = await self.connection.execute(
            text(
                """
                DELETE FROM collections
                WHERE tenant_id = :tenant_id
                  AND tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                  AND id = :collection_id
                """
            ),
            {"tenant_id": tenant_id, "collection_id": collection_id},
        )
        return result.rowcount > 0


def _from_row(row) -> CollectionRecord:
    return CollectionRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        description=row.description,
        indexing_status=row.indexing_status,
        indexing_progress=row.indexing_progress,
        document_count=row.document_count,
        indexed_count=row.indexed_count,
        failed_count=row.failed_count,
        last_indexed_at=row.last_indexed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
