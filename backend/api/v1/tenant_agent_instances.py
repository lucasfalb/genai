from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.rbac import Permission
from app.registry_cache import ToolMetadataCache
from app.responses import api_success
from engine.prompt_cache import PromptCache
from app.schemas import (
    AgentInstanceCreateRequest,
    AgentInstanceResponse,
    AgentInstanceUpdateRequest,
    ApiResponse,
    MessageResponse,
)
from app.workflow_audit import record_tenant_mutation
from database.connection import TenantContext
from database.repositories.agent_instances import AgentInstanceRecord, AgentInstanceRepository
from dependencies.auth import get_connection, require_permission


router = APIRouter(prefix="/tenant/instances", tags=["tenant-agent-instances"])


@router.get(
    "",
    response_model=ApiResponse[list[AgentInstanceResponse]],
    summary="List agent instances",
    description="Lists all agent instances for the selected tenant. Requires Bearer auth, X-Tenant-ID, and agent-instance management permission.",
)
async def list_instances(
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[list[AgentInstanceResponse]]:
    await _set_tenant(connection, context)
    instances = await AgentInstanceRepository(connection).list_instances(tenant_id=context.tenant_id)
    return api_success([_instance_response(i) for i in instances])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[AgentInstanceResponse],
    summary="Create agent instance",
    description="Creates a new agent instance for the selected tenant with inactive status. Requires agent-instance management permission.",
)
async def create_instance(
    payload: AgentInstanceCreateRequest,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[AgentInstanceResponse]:
    await _set_tenant(connection, context)
    instance = await AgentInstanceRepository(connection).create_instance(
        tenant_id=context.tenant_id,
        name=payload.name,
        description=payload.description,
        core_prompt=payload.core_prompt,
        model=payload.model,
        temperature=payload.temperature,
        rag_scope=payload.rag_scope,
        created_by=context.user_id,
    )
    await _after_instance_mutation(
        connection=connection,
        context=context,
        instance=instance,
        action="agent_instance.created",
        metadata=payload.model_dump(),
    )
    return api_success(_instance_response(instance), message="Agent instance created.")


@router.get(
    "/{instance_id}",
    response_model=ApiResponse[AgentInstanceResponse],
    summary="Get agent instance",
    description="Returns details of a single agent instance scoped to the selected tenant.",
)
async def get_instance(
    instance_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[AgentInstanceResponse]:
    await _set_tenant(connection, context)
    instance = await AgentInstanceRepository(connection).get_instance(
        tenant_id=context.tenant_id, instance_id=instance_id
    )
    if instance is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent instance not found")
    return api_success(_instance_response(instance))


@router.patch(
    "/{instance_id}",
    response_model=ApiResponse[AgentInstanceResponse],
    summary="Update agent instance",
    description="Partially updates an agent instance, invalidates tool metadata cache, and records audit/version entries.",
)
async def update_instance(
    instance_id: UUID,
    payload: AgentInstanceUpdateRequest,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[AgentInstanceResponse]:
    if not payload.model_fields_set:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No changes provided")
    await _set_tenant(connection, context)
    instance = await AgentInstanceRepository(connection).update_instance(
        tenant_id=context.tenant_id,
        instance_id=instance_id,
        **payload.model_dump(exclude_unset=True),
    )
    if instance is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent instance not found")
    await ToolMetadataCache(connection).invalidate(tenant_id=context.tenant_id, instance_id=instance_id)
    await PromptCache(connection).invalidate(tenant_id=context.tenant_id, instance_id=instance_id)
    await _after_instance_mutation(
        connection=connection,
        context=context,
        instance=instance,
        action="agent_instance.updated",
        metadata=payload.model_dump(exclude_unset=True),
    )
    return api_success(_instance_response(instance), message="Agent instance updated.")


@router.delete(
    "/{instance_id}",
    response_model=ApiResponse[MessageResponse],
    summary="Archive agent instance",
    description="Archives an agent instance (soft delete) without removing historical sessions or messages, and records audit/version entries.",
)
async def archive_instance(
    instance_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[MessageResponse]:
    await _set_tenant(connection, context)
    instance = await AgentInstanceRepository(connection).archive_instance(
        tenant_id=context.tenant_id, instance_id=instance_id
    )
    if instance is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent instance not found")
    await ToolMetadataCache(connection).invalidate(tenant_id=context.tenant_id, instance_id=instance_id)
    await PromptCache(connection).invalidate(tenant_id=context.tenant_id, instance_id=instance_id)
    await _after_instance_mutation(
        connection=connection,
        context=context,
        instance=instance,
        action="agent_instance.archived",
        metadata={"archived_instance_id": str(instance_id)},
    )
    message = "Agent instance archived."
    return api_success(MessageResponse(message=message), message=message)


async def _set_tenant(connection: AsyncConnection, context: TenantContext) -> None:
    await connection.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(context.tenant_id)},
    )


async def _after_instance_mutation(
    *,
    connection: AsyncConnection,
    context: TenantContext,
    instance: AgentInstanceRecord,
    action: str,
    metadata: dict,
) -> None:
    await record_tenant_mutation(
        connection=connection,
        context=context,
        action=action,
        resource="agent_instances",
        resource_id=str(instance.id),
        snapshot=_instance_response(instance).model_dump(mode="json"),
        metadata=metadata,
    )


def _instance_response(record: AgentInstanceRecord) -> AgentInstanceResponse:
    return AgentInstanceResponse(
        id=record.id,
        tenant_id=record.tenant_id,
        name=record.name,
        description=record.description,
        core_prompt=record.core_prompt,
        model=record.model,
        temperature=record.temperature,
        status=record.status,
        rag_scope=record.rag_scope,
        created_by=record.created_by,
    )
