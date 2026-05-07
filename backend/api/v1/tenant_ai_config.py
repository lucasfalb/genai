from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncConnection

from app.rbac import Permission
from app.responses import api_success
from app.schemas import (
    ApiResponse,
    MessageResponse,
    TenantAIConfigRequest,
    TenantAIConfigResponse,
)
from database.connection import TenantContext
from database.repositories.ai_configs import AIConfigRepository
from dependencies.auth import get_connection, require_permission
from engine.ai_provider import encrypt_api_key

router = APIRouter(prefix="/tenant/ai-config", tags=["tenant-ai-config"])


@router.get(
    "",
    response_model=ApiResponse[TenantAIConfigResponse],
    summary="Get tenant AI config",
    description="Returns the tenant-level AI provider override. API key is never exposed.",
)
async def get_tenant_ai_config(
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[TenantAIConfigResponse]:
    record = await AIConfigRepository(connection).get_tenant_config(tenant_id=context.tenant_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No tenant AI config found")
    return api_success(_tenant_response(record))


@router.put(
    "",
    response_model=ApiResponse[TenantAIConfigResponse],
    summary="Upsert tenant AI config",
    description="Sets or replaces the tenant's own AI provider, overriding the platform default.",
)
async def upsert_tenant_ai_config(
    payload: TenantAIConfigRequest,
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[TenantAIConfigResponse]:
    encrypted = encrypt_api_key(payload.api_key)
    record = await AIConfigRepository(connection).upsert_tenant_config(
        tenant_id=context.tenant_id,
        provider=payload.provider,
        api_key_encrypted=encrypted,
        default_model=payload.default_model,
        base_url=payload.base_url,
    )
    return api_success(_tenant_response(record), message="Tenant AI config updated.")


@router.delete(
    "",
    response_model=ApiResponse[MessageResponse],
    summary="Delete tenant AI config",
    description="Removes the tenant AI override. Tenant falls back to platform AI config.",
)
async def delete_tenant_ai_config(
    context: TenantContext = Depends(require_permission(Permission.MANAGE_AGENT_INSTANCES)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[MessageResponse]:
    deleted = await AIConfigRepository(connection).delete_tenant_config(tenant_id=context.tenant_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No tenant AI config found")
    message = "Tenant AI config deleted."
    return api_success(MessageResponse(message=message), message=message)


def _tenant_response(record) -> TenantAIConfigResponse:
    return TenantAIConfigResponse(
        id=record.id,
        tenant_id=record.tenant_id,
        provider=record.provider,
        default_model=record.default_model,
        base_url=record.base_url,
        is_active=record.is_active,
    )
