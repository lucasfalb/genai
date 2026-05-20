from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection

from app.rbac import Permission
from app.registry_cache import ToolMetadataCache
from app.responses import api_success
from app.schemas import (
    AgentLinkCreateRequest,
    AgentLinkResponse,
    AgentLinkUpdateRequest,
    ApiResponse,
    MessageResponse,
)
from app.workflow_audit import record_tenant_mutation
from database.connection import TenantContext
from database.repositories.agent_links import AgentLinkRecord, AgentLinkRepository
from dependencies.auth import get_connection, require_permission
from engine.prompt_cache import PromptCache


router = APIRouter(prefix="/tenant/instances/{instance_id}/links", tags=["tenant-agent-links"])


@router.get(
    "",
    response_model=ApiResponse[list[AgentLinkResponse]],
    summary="List linked agents",
    description="Lists linked target agents exposed as handoff tools for one source agent instance. Requires Bearer auth, X-Tenant-ID, and handoff management permission.",
)
async def list_agent_links(
    instance_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_HANDOFFS)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[list[AgentLinkResponse]]:
    await _set_tenant(connection, context)
    records = await AgentLinkRepository(connection).list_by_source(
        tenant_id=context.tenant_id,
        source_instance_id=instance_id,
    )
    return api_success([_link_response(record) for record in records])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[AgentLinkResponse],
    summary="Create linked agent",
    description="Creates a tenant-scoped handoff link from the source instance to a target instance, including the tool name, trigger instructions, and context policy used during transfer.",
    responses={
        400: {"description": "Invalid self-link or tool-name collision."},
        404: {"description": "Source or target agent instance not found."},
        409: {"description": "A link or transfer tool name already exists for this source instance."},
    },
)
async def create_agent_link(
    instance_id: UUID,
    payload: AgentLinkCreateRequest,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_HANDOFFS)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[AgentLinkResponse]:
    if instance_id == payload.target_instance_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Source and target agent must be different")
    await _set_tenant(connection, context)
    await _ensure_transfer_tool_name_available(
        connection=connection,
        tenant_id=context.tenant_id,
        instance_id=instance_id,
        transfer_tool_name=payload.transfer_tool_name,
    )
    try:
        record = await AgentLinkRepository(connection).create(
            tenant_id=context.tenant_id,
            source_instance_id=instance_id,
            target_instance_id=payload.target_instance_id,
            transfer_tool_name=payload.transfer_tool_name,
            trigger_description=payload.trigger_description,
            handoff_instructions=payload.handoff_instructions,
            context_policy=payload.context_policy.model_dump(mode="json"),
            transfer_mode=payload.transfer_mode,
            is_enabled=payload.is_enabled,
        )
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Agent link already exists") from exc
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source or target agent instance not found")
    await _after_link_mutation(
        connection=connection,
        context=context,
        source_instance_id=instance_id,
        record=record,
        action="agent_link.created",
        metadata=payload.model_dump(mode="json"),
    )
    return api_success(_link_response(record), message="Linked agent created.")


@router.patch(
    "/{link_id}",
    response_model=ApiResponse[AgentLinkResponse],
    summary="Update linked agent",
    description="Updates handoff tool configuration, transfer instructions, context policy, transfer mode, or enabled state for one linked agent.",
    responses={
        400: {"description": "Invalid update or tool-name collision."},
        404: {"description": "Linked agent not found."},
        409: {"description": "Transfer tool name already exists for this source instance."},
    },
)
async def update_agent_link(
    instance_id: UUID,
    link_id: UUID,
    payload: AgentLinkUpdateRequest,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_HANDOFFS)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[AgentLinkResponse]:
    if not payload.model_fields_set:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No changes provided")
    await _set_tenant(connection, context)
    if payload.transfer_tool_name:
        await _ensure_transfer_tool_name_available(
            connection=connection,
            tenant_id=context.tenant_id,
            instance_id=instance_id,
            transfer_tool_name=payload.transfer_tool_name,
            excluding_link_id=link_id,
        )
    try:
        record = await AgentLinkRepository(connection).update(
            tenant_id=context.tenant_id,
            source_instance_id=instance_id,
            link_id=link_id,
            transfer_tool_name=payload.transfer_tool_name,
            trigger_description=payload.trigger_description,
            handoff_instructions=payload.handoff_instructions,
            context_policy=payload.context_policy.model_dump(mode="json") if payload.context_policy else None,
            transfer_mode=payload.transfer_mode,
            is_enabled=payload.is_enabled,
        )
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Transfer tool name already exists") from exc
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Linked agent not found")
    await _after_link_mutation(
        connection=connection,
        context=context,
        source_instance_id=instance_id,
        record=record,
        action="agent_link.updated",
        metadata=payload.model_dump(mode="json", exclude_unset=True),
    )
    return api_success(_link_response(record), message="Linked agent updated.")


@router.delete(
    "/{link_id}",
    response_model=ApiResponse[MessageResponse],
    summary="Delete linked agent",
    description="Deletes one handoff link from a source agent instance and invalidates prompt-related caches.",
    responses={404: {"description": "Linked agent not found."}},
)
async def delete_agent_link(
    instance_id: UUID,
    link_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_HANDOFFS)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[MessageResponse]:
    await _set_tenant(connection, context)
    record = await AgentLinkRepository(connection).delete(
        tenant_id=context.tenant_id,
        source_instance_id=instance_id,
        link_id=link_id,
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Linked agent not found")
    await _after_link_mutation(
        connection=connection,
        context=context,
        source_instance_id=instance_id,
        record=record,
        action="agent_link.deleted",
        metadata={"deleted_link_id": str(link_id)},
    )
    message = "Linked agent deleted."
    return api_success(MessageResponse(message=message), message=message)


async def _set_tenant(connection: AsyncConnection, context: TenantContext) -> None:
    await connection.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(context.tenant_id)},
    )


async def _ensure_transfer_tool_name_available(
    *,
    connection: AsyncConnection,
    tenant_id: UUID,
    instance_id: UUID,
    transfer_tool_name: str,
    excluding_link_id: UUID | None = None,
) -> None:
    metadata = await ToolMetadataCache(connection).get(tenant_id=tenant_id, instance_id=instance_id)
    active_names = {skill.slug for skill in metadata.skills} | {tool.slug for tool in metadata.tools}
    if transfer_tool_name in active_names:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Transfer tool name conflicts with an active skill or tool")
    result = await connection.execute(
        text(
            """
            SELECT id
            FROM agent_links
            WHERE tenant_id = :tenant_id
              AND source_instance_id = :source_instance_id
              AND transfer_tool_name = :transfer_tool_name
              AND (CAST(:excluding_link_id AS uuid) IS NULL OR id <> CAST(:excluding_link_id AS uuid))
            LIMIT 1
            """
        ),
        {
            "tenant_id": tenant_id,
            "source_instance_id": instance_id,
            "transfer_tool_name": transfer_tool_name,
            "excluding_link_id": excluding_link_id,
        },
    )
    if result.one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Transfer tool name already exists for this source agent")


async def _after_link_mutation(
    *,
    connection: AsyncConnection,
    context: TenantContext,
    source_instance_id: UUID,
    record: AgentLinkRecord,
    action: str,
    metadata: dict,
) -> None:
    await ToolMetadataCache(connection).invalidate(tenant_id=context.tenant_id, instance_id=source_instance_id)
    await PromptCache(connection).invalidate(tenant_id=context.tenant_id, instance_id=source_instance_id)
    await record_tenant_mutation(
        connection=connection,
        context=context,
        action=action,
        resource="agent_links",
        resource_id=str(record.id),
        snapshot=_link_response(record).model_dump(mode="json"),
        metadata=metadata,
    )


def _link_response(record: AgentLinkRecord) -> AgentLinkResponse:
    return AgentLinkResponse(
        id=record.id,
        tenant_id=record.tenant_id,
        source_instance_id=record.source_instance_id,
        target_instance_id=record.target_instance_id,
        target_name=record.target_name,
        target_description=record.target_description,
        transfer_tool_name=record.transfer_tool_name,
        trigger_description=record.trigger_description,
        handoff_instructions=record.handoff_instructions,
        context_policy=record.context_policy,
        transfer_mode=record.transfer_mode,
        is_enabled=record.is_enabled,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
