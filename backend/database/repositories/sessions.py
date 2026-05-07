from dataclasses import dataclass
import json
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
