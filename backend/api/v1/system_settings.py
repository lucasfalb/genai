from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncConnection

from app.responses import api_success
from app.schemas import ApiResponse, PublicSystemSettingsResponse
from database.repositories.ai_configs import AIConfigRepository, SystemSettingsRecord
from dependencies.auth import get_connection

router = APIRouter(prefix="/system-settings", tags=["system-settings"])


@router.get(
    "/public",
    response_model=ApiResponse[PublicSystemSettingsResponse],
    summary="Get public system settings",
    description="Returns only non-sensitive platform settings that the frontend may consume without authentication.",
)
async def get_public_system_settings(
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[PublicSystemSettingsResponse]:
    record = await AIConfigRepository(connection).get_system_settings()
    return api_success(_public_response(record))


def _public_response(record: SystemSettingsRecord) -> PublicSystemSettingsResponse:
    return PublicSystemSettingsResponse(
        platform_name=record.platform_name,
        platform_public_url=record.platform_public_url,
        platform_logo_url=record.platform_logo_url,
        maintenance_mode=record.maintenance_mode,
        registration_enabled=record.registration_enabled,
        public_settings=record.public_settings,
    )
