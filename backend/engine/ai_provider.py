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
    base_url: str | None
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

        platform_cfg = await self._get_platform_config()
        if platform_cfg is not None:
            return platform_cfg

        # Dev fallback: OPENAI_API_KEY in settings (not for production)
        if settings.openai_api_key:
            return ResolvedAIConfig(
                provider="openai",
                api_key=settings.openai_api_key,
                base_url=None,
                default_model="gpt-4.1-mini",
            )

        raise AIProviderNotConfigured(
            "No AI provider configured for this tenant. "
            "Configure via superadmin platform settings or tenant AI config."
        )

    async def _get_tenant_config(self, tenant_id: UUID) -> ResolvedAIConfig | None:
        result = await self.connection.execute(
            text(
                """
                SELECT provider, base_url, api_key_encrypted, default_model
                FROM tenant_ai_configs
                WHERE tenant_id = :tenant_id AND is_active = true
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
            base_url=row.base_url,
            default_model=row.default_model or "gpt-4.1-mini",
        )

    async def _get_platform_config(self) -> ResolvedAIConfig | None:
        result = await self.connection.execute(
            text(
                """
                SELECT provider, base_url, api_key_encrypted, default_model
                FROM platform_ai_configs
                WHERE is_active = true
                ORDER BY created_at DESC
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
            base_url=row.base_url,
            default_model=row.default_model,
        )
