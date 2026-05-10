import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from database.repositories.audit import _redact


@dataclass(frozen=True)
class ResourceVersionRecord:
    id: UUID
    tenant_id: UUID
    resource: str
    resource_id: str
    version_no: int
    action: str
    changed_by: UUID | None
    actor_type: str


class ResourceVersionRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def list_versions(
        self,
        *,
        tenant_id: UUID,
        resource: str,
        resource_id: str,
    ) -> list[dict]:
        result = await self.connection.execute(
            text(
                """
                SELECT rv.id, rv.version_no, rv.action, rv.changed_by, rv.actor_type, rv.actor_role,
                       rv.snapshot, rv.metadata, rv.created_at,
                       u.email AS changed_by_email
                FROM resource_versions rv
                LEFT JOIN users u ON u.id = rv.changed_by
                WHERE rv.tenant_id = :tenant_id
                  AND rv.resource = :resource
                  AND rv.resource_id = :resource_id
                ORDER BY rv.version_no DESC
                """
            ),
            {
                "tenant_id": tenant_id,
                "resource": resource,
                "resource_id": resource_id,
            },
        )
        rows = result.fetchall()
        return [
            {
                "id": str(row.id),
                "version": row.version_no,
                "action": row.action,
                "changed_by": row.changed_by_email or (str(row.changed_by) if row.changed_by else None),
                "actor_type": row.actor_type,
                "actor_role": row.actor_role,
                "snapshot": row.snapshot if row.snapshot else {},
                "metadata": row.metadata if row.metadata else {},
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    async def record(
        self,
        *,
        tenant_id: UUID,
        resource: str,
        resource_id: str,
        action: str,
        changed_by: UUID | None,
        actor_type: str,
        actor_role: str | None = None,
        snapshot: dict | None = None,
        metadata: dict | None = None,
    ) -> ResourceVersionRecord:
        next_version = await self.connection.scalar(
            text(
                """
                SELECT COALESCE(MAX(version_no), 0) + 1
                FROM resource_versions
                WHERE tenant_id = :tenant_id
                  AND resource = :resource
                  AND resource_id = :resource_id
                """
            ),
            {"tenant_id": tenant_id, "resource": resource, "resource_id": resource_id},
        )
        result = await self.connection.execute(
            text(
                """
                INSERT INTO resource_versions
                  (tenant_id, resource, resource_id, version_no, action, changed_by,
                   actor_type, actor_role, snapshot, metadata)
                VALUES
                  (:tenant_id, :resource, :resource_id, :version_no, :action, :changed_by,
                   :actor_type, :actor_role, CAST(:snapshot AS jsonb), CAST(:metadata AS jsonb))
                RETURNING id, tenant_id, resource, resource_id, version_no, action, changed_by, actor_type
                """
            ),
            {
                "tenant_id": tenant_id,
                "resource": resource,
                "resource_id": resource_id,
                "version_no": next_version,
                "action": action,
                "changed_by": changed_by,
                "actor_type": actor_type,
                "actor_role": actor_role,
                "snapshot": json.dumps(_redact(snapshot or {})),
                "metadata": json.dumps(_redact(metadata or {})),
            },
        )
        row = result.one()
        return ResourceVersionRecord(
            id=row.id,
            tenant_id=row.tenant_id,
            resource=row.resource,
            resource_id=row.resource_id,
            version_no=row.version_no,
            action=row.action,
            changed_by=row.changed_by,
            actor_type=row.actor_type,
        )
