import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


SENSITIVE_KEYS = {"api_key", "authorization", "password", "secret", "token"}


@dataclass(frozen=True)
class AuditLogRecord:
    id: UUID
    tenant_id: UUID | None
    user_id: UUID | None
    action: str
    resource: str
    actor_type: str


class AuditLogRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def record(
        self,
        *,
        action: str,
        resource: str,
        tenant_id: UUID | None = None,
        user_id: UUID | None = None,
        resource_id: str | None = None,
        metadata: dict | None = None,
        actor_type: str = "user",
        actor_role: str | None = None,
    ) -> AuditLogRecord:
        result = await self.connection.execute(
            text(
                """
                INSERT INTO audit_logs
                  (tenant_id, user_id, action, resource, resource_id, metadata, actor_type, actor_role)
                VALUES
                  (:tenant_id, :user_id, :action, :resource, :resource_id,
                   CAST(:metadata AS jsonb), :actor_type, :actor_role)
                RETURNING id, tenant_id, user_id, action, resource, actor_type
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "action": action,
                "resource": resource,
                "resource_id": resource_id,
                "metadata": json.dumps(_redact(metadata or {})),
                "actor_type": actor_type,
                "actor_role": actor_role,
            },
        )
        row = result.one()
        return AuditLogRecord(
            id=row.id,
            tenant_id=row.tenant_id,
            user_id=row.user_id,
            action=row.action,
            resource=row.resource,
            actor_type=row.actor_type,
        )


def _redact(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if key.lower() in SENSITIVE_KEYS else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value
