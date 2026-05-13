import json
from dataclasses import dataclass
from datetime import datetime
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


@dataclass(frozen=True)
class AuditLogFullRecord:
    id: UUID
    tenant_id: UUID | None
    user_id: UUID | None
    user_email: str | None
    user_name: str | None
    action: str
    resource: str
    resource_id: str | None
    actor_type: str
    actor_role: str | None
    created_at: datetime
    metadata: dict


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

    async def list_by_tenant(
        self,
        *,
        tenant_id: UUID,
        limit: int = 100,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        action: str | None = None,
        resource: str | None = None,
    ) -> list[AuditLogFullRecord]:
        query = """
            SELECT al.id, al.tenant_id, al.user_id, al.action, al.resource, al.resource_id,
                   al.actor_type, al.actor_role, al.created_at, al.metadata,
                   u.email as user_email, u.name as user_name
            FROM audit_logs al
            LEFT JOIN users u ON al.user_id = u.id
            WHERE al.tenant_id = :tenant_id
        """
        params: dict[str, object] = {"tenant_id": tenant_id, "limit": limit}

        if started_at:
            query += " AND al.created_at >= :started_at"
            params["started_at"] = started_at
        if ended_at:
            query += " AND al.created_at <= :ended_at"
            params["ended_at"] = ended_at
        if action:
            query += " AND al.action = :action"
            params["action"] = action
        if resource:
            query += " AND al.resource = :resource"
            params["resource"] = resource

        query += " ORDER BY al.created_at DESC LIMIT :limit"

        result = await self.connection.execute(text(query), params)
        return [_audit_full_from_row(row) for row in result.fetchall()]


def _audit_full_from_row(row) -> AuditLogFullRecord:
    return AuditLogFullRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        user_id=row.user_id,
        user_email=row.user_email,
        user_name=row.user_name,
        action=row.action,
        resource=row.resource,
        resource_id=row.resource_id,
        actor_type=row.actor_type,
        actor_role=row.actor_role,
        created_at=row.created_at,
        metadata=row.metadata if isinstance(row.metadata, dict) else json.loads(row.metadata or "{}"),
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
