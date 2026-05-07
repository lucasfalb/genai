from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncConnection

from app.rbac import Permission
from app.responses import api_success
from app.schemas import ApiResponse, MessageResponse, TenantAIConfigRequest, TenantAIConfigResponse
from app.workflow_audit import record_tenant_mutation
from database.connection import TenantContext
from database.repositories.ai_configs import AIConfigRepository, TenantAIConfigRecord
from dependencies.auth import get_connection, require_permission
from engine.ai_provider import encrypt_api_key

router = APIRouter(prefix="/tenant/settings/ai", tags=["tenant-ai-settings"])


@router.get(
    "",
    response_model=ApiResponse[TenantAIConfigResponse],
    summary="Get tenant AI settings",
    description="Returns the tenant AI provider override stored on the tenant record. API keys are never exposed.",
)
async def get_tenant_ai_config(
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[TenantAIConfigResponse]:
    record = await AIConfigRepository(connection).get_tenant_config(tenant_id=context.tenant_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
    return api_success(_tenant_response(record))


@router.put(
    "",
    response_model=ApiResponse[TenantAIConfigResponse],
    summary="Upsert tenant AI settings",
    description=(
        "Sets or replaces the tenant AI provider override stored on the tenant record. "
        "The change is written to tenant audit logs and resource versions with actor context."
    ),
)
async def upsert_tenant_ai_config(
    payload: TenantAIConfigRequest,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[TenantAIConfigResponse]:
    encrypted = encrypt_api_key(payload.api_key)
    record = await AIConfigRepository(connection).upsert_tenant_config(
        tenant_id=context.tenant_id,
        configured_by=context.user_id,
        provider=payload.provider,
        api_key_encrypted=encrypted,
        default_model=payload.default_model,
        enabled=payload.enabled,
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
    response = _tenant_response(record)
    await record_tenant_mutation(
        connection=connection,
        context=context,
        action="tenant_ai_settings.updated",
        resource="tenant_ai_settings",
        resource_id=str(context.tenant_id),
        snapshot=response.model_dump(mode="json"),
        metadata={"provider": record.provider, "has_api_key": record.has_api_key},
    )
    return api_success(response, message="Tenant AI settings updated.")


@router.delete(
    "",
    response_model=ApiResponse[MessageResponse],
    summary="Delete tenant AI settings",
    description=(
        "Removes the tenant AI override stored on the tenant record. "
        "The tenant then falls back to global system settings."
    ),
)
async def delete_tenant_ai_config(
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[MessageResponse]:
    record = await AIConfigRepository(connection).delete_tenant_config(
        tenant_id=context.tenant_id,
        configured_by=context.user_id,
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No tenant AI settings found")
    await record_tenant_mutation(
        connection=connection,
        context=context,
        action="tenant_ai_settings.deleted",
        resource="tenant_ai_settings",
        resource_id=str(context.tenant_id),
        snapshot=_tenant_response(record).model_dump(mode="json"),
        metadata={"has_api_key": False},
    )
    message = "Tenant AI settings deleted."
    return api_success(MessageResponse(message=message), message=message)


def _tenant_response(record: TenantAIConfigRecord) -> TenantAIConfigResponse:
    return TenantAIConfigResponse(
        tenant_id=record.tenant_id,
        provider=record.provider,
        default_model=record.default_model,
        enabled=record.enabled,
        has_api_key=record.has_api_key,
        configured_by=record.configured_by,
    )
