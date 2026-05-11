from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncConnection

from app.rbac import Permission
from app.responses import api_success
from app.schemas import ApiResponse, ChatRequest, RunTraceListItem, RunTraceResponse
from database.connection import TenantContext, tenant_connection
from database.repositories.run_traces import RunTraceRecord, RunTraceRepository
from dependencies.auth import get_connection, require_permission
from engine.ai_provider import AIProviderNotConfigured
from engine.bootstrap import AgentInstanceNotFound
from engine.executor import AgentExecutor
from engine.llm_client import LLMProviderError
from engine.session_lock import SessionLockConflict, SessionLockUnavailable


router = APIRouter(prefix="/agent", tags=["agent-chat"])


@router.post(
    "/instances/{instance_id}/chat",
    summary="Stream agent chat response",
    description="Starts one serialized agent run for the selected tenant and instance, persists messages, and streams Server-Sent Events.",
    responses={
        200: {"description": "Server-Sent Events stream with persisted message and completion events."},
        404: {"description": "Agent instance not found in selected tenant."},
        409: {"description": "Session already has an active run."},
        502: {"description": "Configured AI provider is unavailable, unsupported, or not configured."},
    },
)
async def chat(
    instance_id: UUID,
    body: ChatRequest,
    request: Request,
    context: TenantContext = Depends(require_permission(Permission.INTERACT_WITH_AGENTS)),
) -> StreamingResponse:
    connection_context = tenant_connection(context)
    connection = await connection_context.__aenter__()
    try:
        executor = AgentExecutor(connection)
        run = await executor.start_stream(
            tenant_id=context.tenant_id,
            instance_id=instance_id,
            message=body.message,
            session_id=body.session_id,
            channel=body.channel,
            user_ref=str(context.user_id) if context.user_id else None,
            metadata=body.metadata,
        )
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


@router.get(
    "/instances/{instance_id}/runs/latest",
    response_model=ApiResponse[RunTraceResponse],
    summary="Get latest run trace",
    description="Returns the most recent persisted run trace for the instance (optionally scoped by session_id) so the Debug panel can render reasoning, RAG chunks, tool calls and prompt layers.",
    responses={404: {"description": "No trace available for the given filters."}},
)
async def get_latest_trace(
    instance_id: UUID,
    session_id: UUID | None = Query(default=None),
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[RunTraceResponse]:
    repo = RunTraceRepository(connection)
    if session_id is not None:
        record = await repo.get_latest_by_session(tenant_id=context.tenant_id, session_id=session_id)
    else:
        records = await repo.list_by_instance(tenant_id=context.tenant_id, instance_id=instance_id, limit=1)
        record = records[0] if records else None
    if record is None or record.instance_id != instance_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No trace available")
    return api_success(_trace_response(record))


@router.get(
    "/instances/{instance_id}/runs/{run_id}",
    response_model=ApiResponse[RunTraceResponse],
    summary="Get specific run trace",
    description="Returns a persisted run trace by run_id for the Debug panel.",
    responses={404: {"description": "Trace not found."}},
)
async def get_trace(
    instance_id: UUID,
    run_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[RunTraceResponse]:
    record = await RunTraceRepository(connection).get(tenant_id=context.tenant_id, run_id=run_id)
    if record is None or record.instance_id != instance_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trace not found")
    return api_success(_trace_response(record))


@router.get(
    "/instances/{instance_id}/runs",
    response_model=ApiResponse[list[RunTraceListItem]],
    summary="List recent runs",
    description="Lists recent run traces for the instance (optionally filtered by session_id) so the Debug panel can offer history navigation.",
)
async def list_traces(
    instance_id: UUID,
    session_id: UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[list[RunTraceListItem]]:
    repo = RunTraceRepository(connection)
    if session_id is not None:
        records = await repo.list_by_session(tenant_id=context.tenant_id, session_id=session_id, limit=limit)
    else:
        records = await repo.list_by_instance(tenant_id=context.tenant_id, instance_id=instance_id, limit=limit)
    return api_success([_trace_list_item(r) for r in records if r.instance_id == instance_id])


def _trace_response(record: RunTraceRecord) -> RunTraceResponse:
    return RunTraceResponse(
        run_id=record.run_id,
        tenant_id=record.tenant_id,
        instance_id=record.instance_id,
        session_id=record.session_id,
        channel=record.channel,
        trace=record.trace,
        started_at=record.started_at,
        completed_at=record.completed_at,
        created_at=record.created_at,
    )


def _trace_list_item(record: RunTraceRecord) -> RunTraceListItem:
    response_text = record.trace.get("final_response") or ""
    preview = response_text[:240] if response_text else None
    user_msg = record.trace.get("user_message") or None
    duration = record.trace.get("duration_ms")
    if not isinstance(duration, int):
        duration = max(0, int((record.completed_at - record.started_at).total_seconds() * 1000))
    return RunTraceListItem(
        run_id=record.run_id,
        instance_id=record.instance_id,
        session_id=record.session_id,
        started_at=record.started_at,
        completed_at=record.completed_at,
        duration_ms=duration,
        user_message=user_msg,
        final_response_preview=preview,
    )
