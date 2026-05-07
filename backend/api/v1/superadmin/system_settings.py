from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncConnection

from app.responses import api_success
from app.schemas import ApiResponse, SystemSettingsResponse, SystemSettingsUpdateRequest
from database.repositories.ai_configs import AIConfigRepository, SystemSettingsRecord
from database.repositories.audit import AuditLogRepository
from dependencies.auth import CurrentUser, get_connection, require_superadmin
from engine.ai_provider import encrypt_api_key

router = APIRouter(prefix="/superadmin/system-settings", tags=["superadmin-system-settings"])


@router.get(
    "",
    response_model=ApiResponse[SystemSettingsResponse],
    summary="Get system settings",
    description="Returns global platform settings managed by superadmins. Secret values are never exposed.",
)
async def get_system_settings(
    _: CurrentUser = Depends(require_superadmin),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[SystemSettingsResponse]:
    record = await AIConfigRepository(connection).get_system_settings()
    return api_success(_settings_response(record))


@router.patch(
    "",
    response_model=ApiResponse[SystemSettingsResponse],
    summary="Update system settings",
    description=(
        "Updates global platform settings, SMTP settings, global AI fallback, and safe custom settings. "
        "Secrets are encrypted and redacted from responses, audit logs, and version payloads."
    ),
)
async def update_system_settings(
    payload: SystemSettingsUpdateRequest,
    actor: CurrentUser = Depends(require_superadmin),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[SystemSettingsResponse]:
    repository = AIConfigRepository(connection)
    before = await repository.get_system_settings()
    try:
        record = await repository.update_system_settings(
            updated_by=actor.id,
            smtp_pass_encrypted=encrypt_api_key(payload.smtp_pass) if payload.smtp_pass else None,
            ai_api_key_encrypted=encrypt_api_key(payload.ai_api_key) if payload.ai_api_key else None,
            **payload.model_dump(
                exclude_unset=True,
                exclude={"smtp_pass", "ai_api_key"},
            ),
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    await AuditLogRepository(connection).record(
        tenant_id=None,
        user_id=actor.id,
        actor_type="superadmin",
        actor_role="superadmin",
        action="system_settings.updated",
        resource="system_settings",
        resource_id="1",
        metadata={
            "before": _settings_response(before).model_dump(mode="json"),
            "after": _settings_response(record).model_dump(mode="json"),
            "changed_fields": sorted(payload.model_dump(exclude_unset=True).keys()),
        },
    )
    return api_success(_settings_response(record), message="System settings updated.")


def _settings_response(record: SystemSettingsRecord) -> SystemSettingsResponse:
    return SystemSettingsResponse(
        platform_name=record.platform_name,
        platform_public_url=record.platform_public_url,
        platform_logo_url=record.platform_logo_url,
        maintenance_mode=record.maintenance_mode,
        registration_enabled=record.registration_enabled,
        smtp_host=record.smtp_host,
        smtp_port=record.smtp_port,
        smtp_secure=record.smtp_secure,
        smtp_user=record.smtp_user,
        smtp_from=record.smtp_from,
        has_smtp_pass=record.has_smtp_pass,
        ai_provider=record.ai_provider,
        ai_default_model=record.ai_default_model,
        has_ai_api_key=record.has_ai_api_key,
        custom_settings=record.custom_settings,
        public_settings=record.public_settings,
        updated_by=record.updated_by,
    )
