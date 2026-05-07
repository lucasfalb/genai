import json
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


CUSTOM_KEY_PATTERN = re.compile(r"^[a-z0-9_.-]+$")
SENSITIVE_CUSTOM_KEY_PARTS = {
    "api_key",
    "apikey",
    "authorization",
    "password",
    "secret",
    "smtp_pass",
    "token",
}


@dataclass(frozen=True)
class SystemSettingsRecord:
    id: int
    platform_name: str
    platform_public_url: str | None
    platform_logo_url: str | None
    maintenance_mode: bool
    registration_enabled: bool
    smtp_host: str | None
    smtp_port: int
    smtp_secure: bool
    smtp_user: str | None
    smtp_from: str | None
    ai_provider: str
    ai_default_model: str
    has_smtp_pass: bool
    has_ai_api_key: bool
    custom_settings: dict
    public_settings: dict
    updated_by: UUID | None


@dataclass(frozen=True)
class TenantAIConfigRecord:
    tenant_id: UUID
    provider: str | None
    default_model: str | None
    enabled: bool
    has_api_key: bool
    configured_by: UUID | None


class AIConfigRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def get_system_settings(self) -> SystemSettingsRecord:
        await self._ensure_system_settings()
        result = await self.connection.execute(
            text(
                """
                SELECT id, platform_name, platform_public_url, platform_logo_url, maintenance_mode,
                       registration_enabled, smtp_host, smtp_port, smtp_secure,
                       smtp_user, smtp_from, ai_provider,
                       ai_default_model, ai_api_key_encrypted IS NOT NULL AS has_ai_api_key,
                       smtp_pass_encrypted IS NOT NULL AS has_smtp_pass,
                       custom_settings, public_settings, updated_by
                FROM system_settings
                WHERE id = 1
                """
            )
        )
        return _settings_from_row(result.one())

    async def update_system_settings(
        self,
        *,
        updated_by: UUID,
        platform_name: str | None = None,
        platform_public_url: str | None = None,
        platform_logo_url: str | None = None,
        maintenance_mode: bool | None = None,
        registration_enabled: bool | None = None,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        smtp_secure: bool | None = None,
        smtp_user: str | None = None,
        smtp_pass_encrypted: str | None = None,
        smtp_from: str | None = None,
        ai_provider: str | None = None,
        ai_default_model: str | None = None,
        ai_api_key_encrypted: str | None = None,
        custom_settings: dict | None = None,
        public_settings: dict | None = None,
    ) -> SystemSettingsRecord:
        validate_custom_settings(custom_settings)
        validate_custom_settings(public_settings)
        await self._ensure_system_settings()
        result = await self.connection.execute(
            text(
                """
                UPDATE system_settings
                SET
                  platform_name = COALESCE(:platform_name, platform_name),
                  platform_public_url = COALESCE(:platform_public_url, platform_public_url),
                  platform_logo_url = COALESCE(:platform_logo_url, platform_logo_url),
                  maintenance_mode = COALESCE(CAST(:maintenance_mode AS boolean), maintenance_mode),
                  registration_enabled = COALESCE(CAST(:registration_enabled AS boolean), registration_enabled),
                  smtp_host = COALESCE(:smtp_host, smtp_host),
                  smtp_port = COALESCE(:smtp_port, smtp_port),
                  smtp_secure = COALESCE(CAST(:smtp_secure AS boolean), smtp_secure),
                  smtp_user = COALESCE(:smtp_user, smtp_user),
                  smtp_pass_encrypted = COALESCE(:smtp_pass_encrypted, smtp_pass_encrypted),
                  smtp_from = COALESCE(:smtp_from, smtp_from),
                  ai_provider = COALESCE(:ai_provider, ai_provider),
                  ai_default_model = COALESCE(:ai_default_model, ai_default_model),
                  ai_api_key_encrypted = COALESCE(:ai_api_key_encrypted, ai_api_key_encrypted),
                  custom_settings = COALESCE(CAST(:custom_settings AS jsonb), custom_settings),
                  public_settings = COALESCE(CAST(:public_settings AS jsonb), public_settings),
                  updated_by = :updated_by,
                  updated_at = now()
                WHERE id = 1
                RETURNING id, platform_name, platform_public_url, platform_logo_url, maintenance_mode,
                          registration_enabled, smtp_host, smtp_port, smtp_secure,
                          smtp_user, smtp_from, ai_provider,
                          ai_default_model, ai_api_key_encrypted IS NOT NULL AS has_ai_api_key,
                          smtp_pass_encrypted IS NOT NULL AS has_smtp_pass,
                          custom_settings, public_settings, updated_by
                """
            ),
            {
                "updated_by": updated_by,
                "platform_name": platform_name,
                "platform_public_url": platform_public_url,
                "platform_logo_url": platform_logo_url,
                "maintenance_mode": maintenance_mode,
                "registration_enabled": registration_enabled,
                "smtp_host": smtp_host,
                "smtp_port": smtp_port,
                "smtp_secure": smtp_secure,
                "smtp_user": smtp_user,
                "smtp_pass_encrypted": smtp_pass_encrypted,
                "smtp_from": smtp_from,
                "ai_provider": ai_provider,
                "ai_default_model": ai_default_model,
                "ai_api_key_encrypted": ai_api_key_encrypted,
                "custom_settings": None if custom_settings is None else json.dumps(custom_settings),
                "public_settings": None if public_settings is None else json.dumps(public_settings),
            },
        )
        return _settings_from_row(result.one())

    async def get_tenant_config(self, *, tenant_id: UUID) -> TenantAIConfigRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT id AS tenant_id, ai_provider AS provider,
                       ai_default_model AS default_model, ai_enabled AS enabled,
                       ai_api_key_encrypted IS NOT NULL AS has_api_key,
                       ai_configured_by AS configured_by
                FROM tenants
                WHERE id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id},
        )
        row = result.one_or_none()
        return _tenant_from_row(row) if row else None

    async def upsert_tenant_config(
        self,
        *,
        tenant_id: UUID,
        configured_by: UUID,
        provider: str,
        api_key_encrypted: str,
        default_model: str | None = None,
        enabled: bool = True,
    ) -> TenantAIConfigRecord | None:
        result = await self.connection.execute(
            text(
                """
                UPDATE tenants
                SET ai_provider = :provider,
                    ai_api_key_encrypted = :api_key_encrypted,
                    ai_default_model = :default_model,
                    ai_enabled = :enabled,
                    ai_configured_at = now(),
                    ai_configured_by = :configured_by,
                    updated_at = now()
                WHERE id = :tenant_id
                RETURNING id AS tenant_id, ai_provider AS provider,
                          ai_default_model AS default_model, ai_enabled AS enabled,
                          ai_api_key_encrypted IS NOT NULL AS has_api_key,
                          ai_configured_by AS configured_by
                """
            ),
            {
                "tenant_id": tenant_id,
                "configured_by": configured_by,
                "provider": provider,
                "api_key_encrypted": api_key_encrypted,
                "default_model": default_model,
                "enabled": enabled,
            },
        )
        row = result.one_or_none()
        return _tenant_from_row(row) if row else None

    async def delete_tenant_config(self, *, tenant_id: UUID, configured_by: UUID) -> TenantAIConfigRecord | None:
        result = await self.connection.execute(
            text(
                """
                UPDATE tenants
                SET ai_provider = NULL,
                    ai_api_key_encrypted = NULL,
                    ai_default_model = NULL,
                    ai_enabled = false,
                    ai_configured_at = now(),
                    ai_configured_by = :configured_by,
                    updated_at = now()
                WHERE id = :tenant_id
                  AND (ai_api_key_encrypted IS NOT NULL OR ai_enabled = true)
                RETURNING id AS tenant_id, ai_provider AS provider,
                          ai_default_model AS default_model, ai_enabled AS enabled,
                          ai_api_key_encrypted IS NOT NULL AS has_api_key,
                          ai_configured_by AS configured_by
                """
            ),
            {"tenant_id": tenant_id, "configured_by": configured_by},
        )
        row = result.one_or_none()
        return _tenant_from_row(row) if row else None

    async def _ensure_system_settings(self) -> None:
        await self.connection.execute(
            text("INSERT INTO system_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING")
        )


def validate_custom_settings(value: dict | None) -> None:
    if value is None:
        return
    for key in value:
        if not CUSTOM_KEY_PATTERN.fullmatch(key):
            raise ValueError(f"Invalid custom setting key: {key}")
        normalized = key.lower().replace("-", "_").replace(".", "_")
        if any(part in normalized for part in SENSITIVE_CUSTOM_KEY_PARTS):
            raise ValueError(f"Sensitive custom setting key is not allowed: {key}")


def _settings_from_row(row) -> SystemSettingsRecord:
    return SystemSettingsRecord(
        id=row.id,
        platform_name=row.platform_name,
        platform_public_url=row.platform_public_url,
        platform_logo_url=row.platform_logo_url,
        maintenance_mode=row.maintenance_mode,
        registration_enabled=row.registration_enabled,
        smtp_host=row.smtp_host,
        smtp_port=row.smtp_port,
        smtp_secure=row.smtp_secure,
        smtp_user=row.smtp_user,
        smtp_from=row.smtp_from,
        ai_provider=row.ai_provider,
        ai_default_model=row.ai_default_model,
        has_smtp_pass=row.has_smtp_pass,
        has_ai_api_key=row.has_ai_api_key,
        custom_settings=row.custom_settings if isinstance(row.custom_settings, dict) else json.loads(row.custom_settings),
        public_settings=row.public_settings if isinstance(row.public_settings, dict) else json.loads(row.public_settings),
        updated_by=row.updated_by,
    )


def _tenant_from_row(row) -> TenantAIConfigRecord:
    return TenantAIConfigRecord(
        tenant_id=row.tenant_id,
        provider=row.provider,
        default_model=row.default_model,
        enabled=row.enabled,
        has_api_key=row.has_api_key,
        configured_by=row.configured_by,
    )
