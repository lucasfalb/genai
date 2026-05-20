from dataclasses import dataclass
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


@dataclass(frozen=True)
class SessionRecord:
    id: UUID
    tenant_id: UUID
    instance_id: UUID
    channel: str


@dataclass(frozen=True)
class MessageRecord:
    id: UUID
    tenant_id: UUID
    session_id: UUID
    sequence_no: int
    role: str
    content: str


class SessionRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def create_session(
        self,
        *,
        tenant_id: UUID,
        instance_id: UUID,
        channel: str,
        user_ref: str | None = None,
        metadata: dict | None = None,
    ) -> SessionRecord:
        result = await self.connection.execute(
            text(
                """
                INSERT INTO sessions (tenant_id, instance_id, channel, user_ref, metadata)
                VALUES (:tenant_id, :instance_id, :channel, :user_ref, CAST(:metadata AS jsonb))
                RETURNING id, tenant_id, instance_id, channel
                """
            ),
            {
                "tenant_id": tenant_id,
                "instance_id": instance_id,
                "channel": channel,
                "user_ref": user_ref,
                "metadata": json.dumps({} if metadata is None else metadata),
            },
        )
        row = result.one()
        return SessionRecord(id=row.id, tenant_id=row.tenant_id, instance_id=row.instance_id, channel=row.channel)

    async def get_session(self, *, tenant_id: UUID, session_id: UUID, instance_id: UUID | None = None) -> SessionRecord | None:
        filters = "id = :session_id AND tenant_id = :tenant_id"
        params = {"tenant_id": tenant_id, "session_id": session_id}
        if instance_id is not None:
            filters += " AND instance_id = :instance_id"
            params["instance_id"] = instance_id
        result = await self.connection.execute(
            text(
                f"""
                SELECT id, tenant_id, instance_id, channel
                FROM sessions
                WHERE {filters}
                """
            ),
            params,
        )
        row = result.one_or_none()
        return None if row is None else SessionRecord(id=row.id, tenant_id=row.tenant_id, instance_id=row.instance_id, channel=row.channel)

    async def get_latest_session_for_user_ref(
        self,
        *,
        tenant_id: UUID,
        instance_id: UUID,
        channel: str,
        user_ref: str,
    ) -> SessionRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT id, tenant_id, instance_id, channel
                FROM sessions
                WHERE tenant_id = :tenant_id
                  AND instance_id = :instance_id
                  AND channel = :channel
                  AND user_ref = :user_ref
                  AND EXISTS (
                      SELECT 1
                      FROM messages
                      WHERE messages.session_id = sessions.id
                        AND messages.tenant_id = sessions.tenant_id
                  )
                ORDER BY COALESCE(last_message_at, started_at) DESC
                LIMIT 1
                """
            ),
            {
                "tenant_id": tenant_id,
                "instance_id": instance_id,
                "channel": channel,
                "user_ref": user_ref,
            },
        )
        row = result.one_or_none()
        return None if row is None else SessionRecord(id=row.id, tenant_id=row.tenant_id, instance_id=row.instance_id, channel=row.channel)

    async def mark_session_seen(self, *, tenant_id: UUID, session_id: UUID) -> None:
        await self.connection.execute(
            text(
                """
                UPDATE sessions
                SET metadata = jsonb_set(
                    COALESCE(metadata, '{}'::jsonb),
                    '{last_seen_at}',
                    to_jsonb(now()),
                    true
                )
                WHERE id = :session_id AND tenant_id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id, "session_id": session_id},
        )

    async def merge_session_metadata(
        self,
        *,
        tenant_id: UUID,
        session_id: UUID,
        metadata: dict,
    ) -> None:
        if not metadata:
            return
        await self.connection.execute(
            text(
                """
                UPDATE sessions
                SET metadata = COALESCE(metadata, '{}'::jsonb) || CAST(:metadata AS jsonb)
                WHERE id = :session_id AND tenant_id = :tenant_id
                """
            ),
            {
                "tenant_id": tenant_id,
                "session_id": session_id,
                "metadata": json.dumps(metadata),
            },
        )

    async def get_session_summary(
        self,
        *,
        tenant_id: UUID,
        session_id: UUID,
    ) -> dict | None:
        result = await self.connection.execute(
            text(
                """
                SELECT
                    s.id,
                    s.instance_id,
                    s.channel,
                    s.user_ref,
                    s.started_at,
                    s.last_message_at,
                    s.metadata,
                    COUNT(m.id) AS message_count,
                    (
                        s.metadata ? 'last_seen_at'
                        AND (s.metadata->>'last_seen_at')::timestamptz >= (now() - interval '90 seconds')
                    ) AS is_live
                FROM sessions s
                LEFT JOIN messages m ON m.session_id = s.id AND m.tenant_id = s.tenant_id
                WHERE s.id = :session_id AND s.tenant_id = :tenant_id
                GROUP BY s.id
                HAVING COUNT(m.id) > 0
                """
            ),
            {"tenant_id": tenant_id, "session_id": session_id},
        )
        row = result.one_or_none()
        if row is None:
            return None
        return {
            "id": row.id,
            "instance_id": row.instance_id,
            "channel": row.channel,
            "user_ref": row.user_ref,
            "started_at": row.started_at,
            "last_message_at": row.last_message_at,
            "metadata": row.metadata or {},
            "message_count": row.message_count,
            "is_live": row.is_live,
        }

    async def list_messages(self, *, tenant_id: UUID, session_id: UUID, limit: int = 80) -> list[MessageRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT id, tenant_id, session_id, sequence_no, role, content
                FROM messages
                WHERE tenant_id = :tenant_id AND session_id = :session_id
                ORDER BY sequence_no ASC
                LIMIT :limit
                """
            ),
            {"tenant_id": tenant_id, "session_id": session_id, "limit": limit},
        )
        return [
            MessageRecord(
                id=row.id,
                tenant_id=row.tenant_id,
                session_id=row.session_id,
                sequence_no=row.sequence_no,
                role=row.role,
                content=row.content,
            )
            for row in result.fetchall()
        ]

    async def append_message(
        self,
        *,
        tenant_id: UUID,
        session_id: UUID,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> MessageRecord:
        await self.connection.execute(
            text("SELECT id FROM sessions WHERE id = :session_id AND tenant_id = :tenant_id FOR UPDATE"),
            {"session_id": session_id, "tenant_id": tenant_id},
        )
        next_sequence = await self.connection.scalar(
            text(
                """
                SELECT COALESCE(MAX(sequence_no), 0) + 1
                FROM messages
                WHERE session_id = :session_id
                """
            ),
            {"session_id": session_id},
        )
        result = await self.connection.execute(
            text(
                """
                INSERT INTO messages (tenant_id, session_id, sequence_no, role, content, metadata)
                VALUES (:tenant_id, :session_id, :sequence_no, :role, :content, CAST(:metadata AS jsonb))
                RETURNING id, tenant_id, session_id, sequence_no, role, content
                """
            ),
            {
                "tenant_id": tenant_id,
                "session_id": session_id,
                "sequence_no": next_sequence,
                "role": role,
                "content": content,
                "metadata": json.dumps({} if metadata is None else metadata),
            },
        )
        await self.connection.execute(
            text(
                """
                UPDATE sessions
                SET last_message_at = now()
                WHERE id = :session_id AND tenant_id = :tenant_id
                """
            ),
            {"session_id": session_id, "tenant_id": tenant_id},
        )
        row = result.one()
        return MessageRecord(
            id=row.id,
            tenant_id=row.tenant_id,
            session_id=row.session_id,
            sequence_no=row.sequence_no,
            role=row.role,
            content=row.content,
        )

    async def list_sessions(
        self,
        *,
        tenant_id: UUID,
        instance_id: UUID | None = None,
        channel: str | None = None,
        started_from: datetime | None = None,
        started_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        conditions = ["s.tenant_id = :tenant_id"]
        params: dict = {"tenant_id": tenant_id, "limit": limit, "offset": offset}
        if instance_id is not None:
            conditions.append("s.instance_id = :instance_id")
            params["instance_id"] = instance_id
        if channel is not None:
            conditions.append("s.channel = :channel")
            params["channel"] = channel
        if started_from is not None:
            conditions.append("s.started_at >= :started_from")
            params["started_from"] = started_from
        if started_to is not None:
            conditions.append("s.started_at <= :started_to")
            params["started_to"] = started_to
        where = " AND ".join(conditions)
        result = await self.connection.execute(
            text(
                f"""
                SELECT
                    s.id,
                    s.instance_id,
                    s.channel,
                    s.user_ref,
                    s.started_at,
                    s.last_message_at,
                    s.metadata,
                    COUNT(m.id) AS message_count,
                    (
                        s.metadata ? 'last_seen_at'
                        AND (s.metadata->>'last_seen_at')::timestamptz >= (now() - interval '90 seconds')
                    ) AS is_live
                FROM sessions s
                LEFT JOIN messages m ON m.session_id = s.id AND m.tenant_id = s.tenant_id
                WHERE {where}
                GROUP BY s.id
                HAVING COUNT(m.id) > 0
                ORDER BY COALESCE(s.last_message_at, s.started_at) DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        return [
            {
                "id": row.id,
                "instance_id": row.instance_id,
                "channel": row.channel,
                "user_ref": row.user_ref,
                "started_at": row.started_at,
                "last_message_at": row.last_message_at,
                "metadata": row.metadata or {},
                "message_count": row.message_count,
                "is_live": row.is_live,
            }
            for row in result.fetchall()
        ]
