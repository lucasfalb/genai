import json
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import Field
from sqlalchemy import text

from app.responses import api_success
from app.geoip import merge_environment
from app.schemas import ApiResponse, BaseModel, ChatRequest
from database.connection import TenantContext, engine, tenant_connection
from database.repositories.sessions import SessionRepository
from engine.ai_provider import AIProviderNotConfigured
from engine.bootstrap import AgentInstanceNotFound
from engine.executor import AgentExecutor
from engine.llm_client import LLMProviderError
from engine.session_lock import SessionLockConflict, SessionLockUnavailable


router = APIRouter(prefix="/public/widget", tags=["public-widget"])


class PublicWidgetMessage(BaseModel):
    role: str
    content: str


class PublicWidgetSessionRequest(BaseModel):
    visitor_id: str = Field(min_length=8, max_length=160)


class PublicWidgetSessionResponse(BaseModel):
    session_id: UUID | None = None
    messages: list[PublicWidgetMessage]


async def _resolve_widget(
    instance_id: UUID,
    request: Request,
) -> tuple[UUID, dict, list[str]]:
    """Verify the widget channel is active, check origin, and return config + allowed_origins."""
    async with engine.begin() as conn:
        tenant_rows = await conn.execute(text("SELECT id FROM tenants WHERE status = 'active'"))
        row = None
        tenant_id = None
        for tenant in tenant_rows.fetchall():
            await conn.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": str(tenant.id)},
            )
            result = await conn.execute(
                text(
                    """
                    SELECT tenant_id, config, allowed_origins, is_active
                    FROM agent_channel_configs
                    WHERE instance_id = :iid AND channel = 'widget'
                    """
                ),
                {"iid": str(instance_id)},
            )
            row = result.fetchone()
            if row is not None:
                tenant_id = row.tenant_id
                break

    if not row or not row.is_active or tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Web widget is not active for this instance",
        )

    allowed_origins: list[str] = list(row.allowed_origins or [])

    if allowed_origins:
        origin = request.headers.get("origin") or ""
        if origin and not any(o == origin or origin.endswith(o.lstrip("*")) for o in allowed_origins):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Origin not allowed",
            )

    raw_config = row.config
    if isinstance(raw_config, str):
        raw_config = json.loads(raw_config)

    return tenant_id, raw_config or {}, allowed_origins


@router.get(
    "/{instance_id}/config",
    summary="Get public widget config",
    description="Returns the widget configuration for an active web widget channel. No authentication required.",
    tags=["public-widget"],
)
async def get_widget_config(
    instance_id: UUID,
    request: Request = ...,
):
    _, config, _ = await _resolve_widget(instance_id, request)
    return api_success(config)


@router.post(
    "/{instance_id}/session",
    response_model=ApiResponse[PublicWidgetSessionResponse],
    summary="Get public widget session",
    description="Returns the latest server-side widget session with messages for the visitor. No authentication required.",
    tags=["public-widget"],
)
async def get_widget_session(
    instance_id: UUID,
    body: PublicWidgetSessionRequest,
    request: Request = ...,
) -> ApiResponse[PublicWidgetSessionResponse]:
    tenant_id, _, _ = await _resolve_widget(instance_id, request)
    context = TenantContext(tenant_id=tenant_id)

    async with tenant_connection(context) as connection:
        repository = SessionRepository(connection)
        session = await repository.get_latest_session_for_user_ref(
            tenant_id=tenant_id,
            instance_id=instance_id,
            channel="widget",
            user_ref=body.visitor_id,
        )
        if session is not None:
            await repository.mark_session_seen(tenant_id=tenant_id, session_id=session.id)
            records = await repository.list_messages(tenant_id=tenant_id, session_id=session.id)
            messages = [
                PublicWidgetMessage(role=record.role, content=record.content)
                for record in records
                if record.role in {"user", "assistant"}
            ]
        else:
            messages = []

    return api_success(
        PublicWidgetSessionResponse(session_id=session.id if session is not None else None, messages=messages)
    )


@router.post(
    "/{instance_id}/chat",
    summary="Public widget chat stream",
    description="Streams SSE chat responses for an active web widget channel. No authentication required.",
    tags=["public-widget"],
)
async def widget_chat(
    instance_id: UUID,
    body: ChatRequest,
    request: Request = ...,
) -> StreamingResponse:
    tenant_id, _, _ = await _resolve_widget(instance_id, request)

    context = TenantContext(tenant_id=tenant_id)
    connection_context = tenant_connection(context)
    connection = await connection_context.__aenter__()

    try:
        executor = AgentExecutor(connection)
        visitor_id = body.metadata.get("visitor_id") if isinstance(body.metadata, dict) else None
        widget_user_ref = visitor_id if isinstance(visitor_id, str) and 8 <= len(visitor_id) <= 160 else None
        metadata = merge_environment(body.metadata if isinstance(body.metadata, dict) else {}, request)
        run = await executor.start_stream(
            tenant_id=tenant_id,
            instance_id=instance_id,
            message=body.message,
            session_id=body.session_id,
            channel="widget",
            user_ref=widget_user_ref,
            metadata=metadata,
        )
        repository = SessionRepository(connection)
        await repository.merge_session_metadata(
            tenant_id=tenant_id,
            session_id=run.session_id,
            metadata=metadata,
        )
        await repository.mark_session_seen(tenant_id=tenant_id, session_id=run.session_id)
    except AgentInstanceNotFound as exc:
        await connection_context.__aexit__(type(exc), exc, exc.__traceback__)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent instance not found") from exc
    except SessionLockConflict as exc:
        await connection_context.__aexit__(type(exc), exc, exc.__traceback__)
        raise HTTPException(status.HTTP_409_CONFLICT, "Session already has an active run") from exc
    except SessionLockUnavailable as exc:
        await connection_context.__aexit__(type(exc), exc, exc.__traceback__)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Session lock unavailable") from exc
    except (AIProviderNotConfigured, LLMProviderError) as exc:
        await connection_context.__aexit__(type(exc), exc, exc.__traceback__)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "AI provider unavailable") from exc
    except Exception as exc:
        await connection_context.__aexit__(type(exc), exc, exc.__traceback__)
        raise

    async def event_stream():
        try:
            async for event in run.events():
                if await request.is_disconnected():
                    await run.cancel()
                    break
                yield AgentExecutor.encode_sse(event)
        finally:
            await run.close()
            await connection_context.__aexit__(None, None, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
