from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.rbac import Permission
from app.schemas import ChatRequest
from database.connection import TenantContext, tenant_connection
from dependencies.auth import require_permission
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
