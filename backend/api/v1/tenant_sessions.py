from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncConnection

from app.rbac import Permission
from app.responses import api_success
from app.schemas import ApiResponse, SessionListItem, SessionMessageItem
from database.connection import TenantContext
from database.repositories.sessions import SessionRepository
from dependencies.auth import get_connection, require_permission

router = APIRouter(prefix="/tenant/sessions", tags=["tenant-sessions"])


@router.get(
    "",
    response_model=ApiResponse[list[SessionListItem]],
    summary="List sessions",
    description="Returns chat sessions for the active tenant, with optional filters by agent, channel, or date range.",
)
async def list_sessions(
    context: TenantContext = Depends(require_permission(Permission.VIEW_LOGS)),
    connection: AsyncConnection = Depends(get_connection),
    instance_id: UUID | None = Query(None),
    channel: str | None = Query(None, max_length=80),
    started_from: datetime | None = Query(None),
    started_to: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApiResponse[list[SessionListItem]]:
    rows = await SessionRepository(connection).list_sessions(
        tenant_id=context.tenant_id,
        instance_id=instance_id,
        channel=channel,
        started_from=started_from,
        started_to=started_to,
        limit=limit,
        offset=offset,
    )
    return api_success(
        [
            SessionListItem(
                id=r["id"],
                instance_id=r["instance_id"],
                channel=r["channel"],
                user_ref=r["user_ref"],
                started_at=r["started_at"],
                last_message_at=r["last_message_at"],
                message_count=r["message_count"],
                is_live=r["is_live"],
                environment=_session_environment(r),
            )
            for r in rows
        ]
    )


@router.get(
    "/{session_id}",
    response_model=ApiResponse[SessionListItem],
    summary="Get session details",
    description="Returns metadata for a single tenant session, including message count and live activity status.",
)
async def get_session(
    session_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.VIEW_LOGS)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[SessionListItem]:
    row = await SessionRepository(connection).get_session_summary(
        tenant_id=context.tenant_id,
        session_id=session_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return api_success(
        SessionListItem(
            id=row["id"],
            instance_id=row["instance_id"],
            channel=row["channel"],
            user_ref=row["user_ref"],
            started_at=row["started_at"],
            last_message_at=row["last_message_at"],
            message_count=row["message_count"],
            is_live=row["is_live"],
            environment=_session_environment(row),
        )
    )


@router.get(
    "/{session_id}/messages",
    response_model=ApiResponse[list[SessionMessageItem]],
    summary="List session messages",
    description="Returns the full message history for a single session.",
)
async def list_session_messages(
    session_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.VIEW_LOGS)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[list[SessionMessageItem]]:
    repo = SessionRepository(connection)
    session = await repo.get_session(tenant_id=context.tenant_id, session_id=session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = await repo.list_messages(
        tenant_id=context.tenant_id,
        session_id=session_id,
        limit=500,
    )
    return api_success(
        [
            SessionMessageItem(
                id=m.id,
                session_id=m.session_id,
                sequence_no=m.sequence_no,
                role=m.role,
                content=m.content,
            )
            for m in messages
        ]
    )


def _session_environment(row: dict) -> dict | None:
    metadata = row.get("metadata") if isinstance(row, dict) else None
    if not isinstance(metadata, dict):
        return None
    environment = metadata.get("environment")
    return environment if isinstance(environment, dict) else None
