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

DEFAULT_PUBLIC_SETTINGS = {
    "agent_ui": {
        "default_model": "gpt-5-mini",
        "models": [
            {"value": "gpt-5-mini", "label": "GPT-5 Mini"},
            {"value": "gpt-5", "label": "GPT-5"},
            {"value": "gpt-4o-mini", "label": "GPT-4o Mini"},
            {"value": "gpt-4o", "label": "GPT-4o"},
            {"value": "gpt-4.1-mini", "label": "GPT-4.1 Mini"},
        ],
        "templates": [
            {
                "name": "Support Agent",
                "description": "Answers customer questions using tenant knowledge and clear escalation rules.",
                "core_prompt": "You are a support agent. Answer clearly, use available knowledge, and escalate when confidence is low.",
            },
            {
                "name": "Sales Assistant",
                "description": "Qualifies leads, explains offers, and prepares next-step summaries.",
                "core_prompt": "You are a sales assistant. Ask concise qualifying questions and recommend the next best action.",
            },
            {
                "name": "Knowledge Analyst",
                "description": "Researches tenant documents and produces structured answers with citations when possible.",
                "core_prompt": "You are a knowledge analyst. Synthesize information from approved sources and explain uncertainty.",
            },
        ],
    }
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
class ProviderConfig:
    name: str
    enabled: bool
    has_api_key: bool
    api_key_hint: str | None
    configured_at: str | None
    configured_by: str | None


@dataclass(frozen=True)
class TenantProvidersRecord:
    tenant_id: UUID
    providers: list[ProviderConfig]


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

    async def get_tenant_providers(self, *, tenant_id: UUID) -> TenantProvidersRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT id AS tenant_id, providers_config
                FROM tenants
                WHERE id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id},
        )
        row = result.one_or_none()
        return _tenant_providers_from_row(row) if row else None

    async def upsert_provider(
        self,
        *,
        tenant_id: UUID,
        configured_by: UUID,
        provider_name: str,
        api_key_encrypted: str | None = None,
        api_key_hint: str | None = None,
        enabled: bool | None = None,
    ) -> TenantProvidersRecord | None:
        if api_key_encrypted is not None:
            result = await self.connection.execute(
                text(
                    """
                    UPDATE tenants
                    SET providers_config = jsonb_set(
                          COALESCE(providers_config, '{"providers": []}'::jsonb),
                          '{providers}',
                          COALESCE(
                            (
                              SELECT jsonb_agg(
                                CASE
                                  WHEN elem->>'name' = :provider_name THEN
                                    jsonb_build_object(
                                      'name', :provider_name,
                                      'api_key_encrypted', CAST(:api_key_encrypted AS text),
                                      'api_key_hint', CAST(:api_key_hint AS text),
                                      'enabled', true,
                                      'configured_at', to_char(now(), 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
                                      'configured_by', CAST(:configured_by AS text)
                                    )
                                  ELSE elem
                                END
                              )
                              FROM jsonb_array_elements(providers_config->'providers') AS elem
                              WHERE elem->>'name' != :provider_name
                            ),
                            '[]'::jsonb
                          ) || jsonb_build_array(
                            jsonb_build_object(
                              'name', :provider_name,
                              'api_key_encrypted', CAST(:api_key_encrypted AS text),
                              'api_key_hint', CAST(:api_key_hint AS text),
                              'enabled', true,
                              'configured_at', to_char(now(), 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
                              'configured_by', CAST(:configured_by AS text)
                            )
                          )
                        ),
                        updated_at = now()
                    WHERE id = :tenant_id
                    RETURNING id AS tenant_id, providers_config
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "configured_by": str(configured_by),
                    "provider_name": provider_name,
                    "api_key_encrypted": api_key_encrypted,
                    "api_key_hint": api_key_hint,
                },
            )
        else:
            result = await self.connection.execute(
                text(
                    """
                    UPDATE tenants
                    SET providers_config = jsonb_set(
                          providers_config,
                          '{providers}',
                          (
                            SELECT jsonb_agg(
                              CASE
                                WHEN elem->>'name' = :provider_name THEN
                                  elem || jsonb_build_object('enabled', CAST(:enabled AS boolean))
                                ELSE elem
                              END
                            )
                            FROM jsonb_array_elements(providers_config->'providers') AS elem
                          )
                        ),
                        updated_at = now()
                    WHERE id = :tenant_id
                      AND providers_config->'providers' @> jsonb_build_array(jsonb_build_object('name', CAST(:provider_name AS text)))
                    RETURNING id AS tenant_id, providers_config
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "provider_name": provider_name,
                    "enabled": enabled,
                },
            )
        row = result.one_or_none()
        return _tenant_providers_from_row(row) if row else None

    async def delete_provider(
        self, *, tenant_id: UUID, provider_name: str
    ) -> TenantProvidersRecord | None:
        result = await self.connection.execute(
            text(
                """
                UPDATE tenants
                SET providers_config = jsonb_set(
                      providers_config,
                      '{providers}',
                      COALESCE(
                        (
                          SELECT jsonb_agg(elem)
                          FROM jsonb_array_elements(providers_config->'providers') AS elem
                          WHERE elem->>'name' != :provider_name
                        ),
                        '[]'::jsonb
                      )
                    ),
                    updated_at = now()
                WHERE id = :tenant_id
                RETURNING id AS tenant_id, providers_config
                """
            ),
            {"tenant_id": tenant_id, "provider_name": provider_name},
        )
        row = result.one_or_none()
        return _tenant_providers_from_row(row) if row else None

    async def get_provider_encrypted_key(self, *, tenant_id: UUID, provider_name: str) -> str | None:
        result = await self.connection.execute(
            text("SELECT providers_config FROM tenants WHERE id = :tenant_id"),
            {"tenant_id": tenant_id},
        )
        row = result.one_or_none()
        if row is None:
            return None
        config = row.providers_config if isinstance(row.providers_config, dict) else json.loads(row.providers_config)
        for p in config.get("providers", []):
            if p.get("name") == provider_name:
                return p.get("api_key_encrypted")
        return None

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
    public_settings = (
        row.public_settings if isinstance(row.public_settings, dict) else json.loads(row.public_settings)
    )
    public_settings = {**DEFAULT_PUBLIC_SETTINGS, **public_settings}
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
        public_settings=public_settings,
        updated_by=row.updated_by,
    )


def _tenant_providers_from_row(row) -> TenantProvidersRecord:
    config = row.providers_config if isinstance(row.providers_config, dict) else json.loads(row.providers_config)
    providers_list = config.get("providers", [])

    providers = []
    for p in providers_list:
        providers.append(
            ProviderConfig(
                name=p.get("name", ""),
                enabled=p.get("enabled", False),
                has_api_key=bool(p.get("api_key_encrypted")),
                api_key_hint=p.get("api_key_hint"),
                configured_at=p.get("configured_at"),
                configured_by=p.get("configured_by"),
            )
        )

    return TenantProvidersRecord(
        tenant_id=row.tenant_id,
        providers=providers,
    )
