from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.config import settings


class AIProviderNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class ResolvedAIConfig:
    provider: str
    api_key: str
    default_model: str


def encrypt_api_key(plaintext: str) -> str:
    from cryptography.fernet import Fernet
    if not settings.ai_config_encryption_key:
        raise RuntimeError("AI_CONFIG_ENCRYPTION_KEY not configured")
    return Fernet(settings.ai_config_encryption_key.encode()).encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    from cryptography.fernet import Fernet
    if not settings.ai_config_encryption_key:
        raise RuntimeError("AI_CONFIG_ENCRYPTION_KEY not configured")
    return Fernet(settings.ai_config_encryption_key.encode()).decrypt(ciphertext.encode()).decode()


class AIProviderResolver:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def resolve(self, *, tenant_id: UUID) -> ResolvedAIConfig:
        tenant_cfg = await self._get_tenant_config(tenant_id)
        if tenant_cfg is not None:
            return tenant_cfg

        system_cfg = await self._get_system_settings()
        if system_cfg is not None:
            return system_cfg

        # Dev fallback: OPENAI_API_KEY in settings (not for production)
        if settings.openai_api_key:
            return ResolvedAIConfig(
                provider="openai",
                api_key=settings.openai_api_key,
                default_model="gpt-4.1-mini",
            )

        raise AIProviderNotConfigured(
            "No AI provider configured for this tenant. "
            "Configure via superadmin system settings or tenant AI settings."
        )

    async def _get_tenant_config(self, tenant_id: UUID) -> ResolvedAIConfig | None:
        result = await self.connection.execute(
            text(
                """
                SELECT ai_provider AS provider,
                       ai_api_key_encrypted AS api_key_encrypted,
                       ai_default_model AS default_model
                FROM tenants
                WHERE id = :tenant_id
                  AND ai_enabled = true
                  AND ai_api_key_encrypted IS NOT NULL
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id},
        )
        row = result.one_or_none()
        if row is None:
            return None
        return ResolvedAIConfig(
            provider=row.provider,
            api_key=decrypt_api_key(row.api_key_encrypted),
            default_model=row.default_model or "gpt-4.1-mini",
        )

    async def _get_system_settings(self) -> ResolvedAIConfig | None:
        result = await self.connection.execute(
            text(
                """
                SELECT ai_provider AS provider,
                       ai_api_key_encrypted AS api_key_encrypted,
                       ai_default_model AS default_model
                FROM system_settings
                WHERE id = 1
                  AND ai_api_key_encrypted IS NOT NULL
                LIMIT 1
                """
            ),
        )
        row = result.one_or_none()
        if row is None:
            return None
        return ResolvedAIConfig(
            provider=row.provider,
            api_key=decrypt_api_key(row.api_key_encrypted),
            default_model=row.default_model,
        )
