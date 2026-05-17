from fastapi import APIRouter, Depends
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncConnection

from app.cache import redis_client
from app.responses import api_success
from app.schemas import ApiResponse, PublicSystemSettingsResponse
from database.repositories.ai_configs import AIConfigRepository, SystemSettingsRecord
from dependencies.auth import get_connection

router = APIRouter(prefix="/system-settings", tags=["system-settings"])

SYSTEM_SETTINGS_PUBLIC_KEY = "system:settings:public"


@router.get(
    "/public",
    response_model=ApiResponse[PublicSystemSettingsResponse],
    summary="Get public system settings",
    description="Returns only non-sensitive platform settings that the frontend may consume without authentication.",
)
async def get_public_system_settings(
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[PublicSystemSettingsResponse]:
    try:
        cached = await redis_client.get(SYSTEM_SETTINGS_PUBLIC_KEY)
        if cached:
            return api_success(PublicSystemSettingsResponse.model_validate_json(cached))
    except (RedisError, RuntimeError):
        pass

    record = await AIConfigRepository(connection).get_system_settings()
    response = _public_response(record)
    try:
        await redis_client.setex(SYSTEM_SETTINGS_PUBLIC_KEY, 60, response.model_dump_json())
    except (RedisError, RuntimeError):
        pass
    return api_success(response)


def _public_response(record: SystemSettingsRecord) -> PublicSystemSettingsResponse:
    return PublicSystemSettingsResponse(
        platform_name=record.platform_name,
        platform_public_url=record.platform_public_url,
        platform_logo_url=record.platform_logo_url,
        maintenance_mode=record.maintenance_mode,
        registration_enabled=record.registration_enabled,
        public_settings=record.public_settings,
    )
