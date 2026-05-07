from fastapi import APIRouter, Depends, HTTPException, status

from app.responses import api_success
from app.schemas import (
    ApiResponse,
    MessageResponse,
    PlatformAIConfigRequest,
    PlatformAIConfigResponse,
)
from database.repositories.ai_configs import AIConfigRepository
from dependencies.auth import get_connection, require_superadmin
from engine.ai_provider import encrypt_api_key
from sqlalchemy.ext.asyncio import AsyncConnection

router = APIRouter(prefix="/superadmin/ai-config", tags=["superadmin-ai-config"])


@router.get(
    "",
    response_model=ApiResponse[PlatformAIConfigResponse],
    summary="Get platform AI config",
    description="Returns the active platform-level AI provider config. API key is never exposed.",
)
async def get_platform_ai_config(
    _: None = Depends(require_superadmin),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[PlatformAIConfigResponse]:
    record = await AIConfigRepository(connection).get_platform_config()
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No platform AI config found")
    return api_success(_platform_response(record))


@router.put(
    "",
    response_model=ApiResponse[PlatformAIConfigResponse],
    summary="Upsert platform AI config",
    description="Sets or replaces the platform-level AI provider config. Previous active config is deactivated.",
)
async def upsert_platform_ai_config(
    payload: PlatformAIConfigRequest,
    _: None = Depends(require_superadmin),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[PlatformAIConfigResponse]:
    encrypted = encrypt_api_key(payload.api_key)
    record = await AIConfigRepository(connection).upsert_platform_config(
        provider=payload.provider,
        api_key_encrypted=encrypted,
        default_model=payload.default_model,
        base_url=payload.base_url,
    )
    return api_success(_platform_response(record), message="Platform AI config updated.")


@router.delete(
    "",
    response_model=ApiResponse[MessageResponse],
    summary="Delete platform AI config",
    description="Removes the active platform AI config. Tenants without their own config will lose AI access.",
)
async def delete_platform_ai_config(
    _: None = Depends(require_superadmin),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[MessageResponse]:
    deleted = await AIConfigRepository(connection).delete_platform_config()
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No active platform AI config found")
    message = "Platform AI config deleted."
    return api_success(MessageResponse(message=message), message=message)


def _platform_response(record) -> PlatformAIConfigResponse:
    return PlatformAIConfigResponse(
        id=record.id,
        provider=record.provider,
        default_model=record.default_model,
        base_url=record.base_url,
        is_active=record.is_active,
    )
