import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


@dataclass(frozen=True)
class RunTraceRecord:
    run_id: UUID
    tenant_id: UUID
    instance_id: UUID
    session_id: UUID
    channel: str
    trace: dict
    started_at: datetime
    completed_at: datetime
    created_at: datetime


class RunTraceRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def create(
        self,
        *,
        run_id: UUID,
        tenant_id: UUID,
        instance_id: UUID,
        session_id: UUID,
        channel: str,
        trace: dict,
        started_at: datetime,
        completed_at: datetime,
    ) -> RunTraceRecord:
        result = await self.connection.execute(
            text(
                """
                INSERT INTO agent_run_traces (
                    run_id, tenant_id, instance_id, session_id, channel,
                    trace, started_at, completed_at
                )
                VALUES (
                    :run_id, :tenant_id, :instance_id, :session_id, :channel,
                    CAST(:trace AS jsonb), :started_at, :completed_at
                )
                RETURNING run_id, tenant_id, instance_id, session_id, channel,
                          trace, started_at, completed_at, created_at
                """
            ),
            {
                "run_id": run_id,
                "tenant_id": tenant_id,
                "instance_id": instance_id,
                "session_id": session_id,
                "channel": channel,
                "trace": json.dumps(trace),
                "started_at": started_at,
                "completed_at": completed_at,
            },
        )
        return _from_row(result.one())

    async def get(self, *, tenant_id: UUID, run_id: UUID) -> RunTraceRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT run_id, tenant_id, instance_id, session_id, channel,
                       trace, started_at, completed_at, created_at
                FROM agent_run_traces
                WHERE tenant_id = :tenant_id AND run_id = :run_id
                """
            ),
            {"tenant_id": tenant_id, "run_id": run_id},
        )
        row = result.one_or_none()
        return _from_row(row) if row else None

    async def get_latest_by_session(
        self, *, tenant_id: UUID, session_id: UUID
    ) -> RunTraceRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT run_id, tenant_id, instance_id, session_id, channel,
                       trace, started_at, completed_at, created_at
                FROM agent_run_traces
                WHERE tenant_id = :tenant_id AND session_id = :session_id
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id, "session_id": session_id},
        )
        row = result.one_or_none()
        return _from_row(row) if row else None

    async def list_by_session(
        self, *, tenant_id: UUID, session_id: UUID, limit: int = 50
    ) -> list[RunTraceRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT run_id, tenant_id, instance_id, session_id, channel,
                       trace, started_at, completed_at, created_at
                FROM agent_run_traces
                WHERE tenant_id = :tenant_id AND session_id = :session_id
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"tenant_id": tenant_id, "session_id": session_id, "limit": limit},
        )
        return [_from_row(row) for row in result.fetchall()]

    async def list_by_instance(
        self, *, tenant_id: UUID, instance_id: UUID, limit: int = 50
    ) -> list[RunTraceRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT run_id, tenant_id, instance_id, session_id, channel,
                       trace, started_at, completed_at, created_at
                FROM agent_run_traces
                WHERE tenant_id = :tenant_id AND instance_id = :instance_id
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"tenant_id": tenant_id, "instance_id": instance_id, "limit": limit},
        )
        return [_from_row(row) for row in result.fetchall()]


def _from_row(row) -> RunTraceRecord:
    trace = row.trace if isinstance(row.trace, dict) else json.loads(row.trace)
    return RunTraceRecord(
        run_id=row.run_id,
        tenant_id=row.tenant_id,
        instance_id=row.instance_id,
        session_id=row.session_id,
        channel=row.channel,
        trace=trace,
        started_at=row.started_at,
        completed_at=row.completed_at,
        created_at=row.created_at,
    )
