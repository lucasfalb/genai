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
