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

    async def resolve_embedding_api_key(self, *, tenant_id: UUID) -> str | None:
        """Return an OpenAI API key suitable for embeddings.

        Priority:
        1. Tenant's openai provider entry (if enabled + has key)
        2. System settings ai_api_key when ai_provider == 'openai'
        3. settings.openai_embedding_api_key / settings.openai_api_key (env)
        """
        result = await self.connection.execute(
            text(
                """
                SELECT provider->>'api_key_encrypted' AS api_key_encrypted
                FROM tenants,
                     LATERAL jsonb_array_elements(
                       COALESCE(providers_config->'providers', '[]'::jsonb)
                     ) AS provider
                WHERE id = :tenant_id
                  AND provider->>'name' = 'openai'
                  AND COALESCE((provider->>'enabled')::boolean, false) = true
                  AND provider->>'api_key_encrypted' IS NOT NULL
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id},
        )
        row = result.one_or_none()
        if row is not None and row.api_key_encrypted:
            return decrypt_api_key(row.api_key_encrypted)

        sys_result = await self.connection.execute(
            text(
                """
                SELECT ai_api_key_encrypted
                FROM system_settings
                WHERE id = 1
                  AND ai_provider = 'openai'
                  AND ai_api_key_encrypted IS NOT NULL
                LIMIT 1
                """
            ),
        )
        sys_row = sys_result.one_or_none()
        if sys_row is not None and sys_row.ai_api_key_encrypted:
            return decrypt_api_key(sys_row.ai_api_key_encrypted)

        return settings.openai_embedding_api_key or settings.openai_api_key or None

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
                default_model="gpt-5-mini",
            )

        raise AIProviderNotConfigured(
            "No AI provider configured for this tenant. "
            "Configure via superadmin system settings or tenant AI settings."
        )

    async def _get_tenant_config(self, tenant_id: UUID) -> ResolvedAIConfig | None:
        result = await self.connection.execute(
            text(
                """
                SELECT provider->>'name' AS provider,
                       provider->>'api_key_encrypted' AS api_key_encrypted,
                       provider->>'default_model' AS default_model
                FROM tenants,
                     LATERAL jsonb_array_elements(
                       COALESCE(providers_config->'providers', '[]'::jsonb)
                     ) AS provider
                WHERE id = :tenant_id
                  AND COALESCE((provider->>'enabled')::boolean, false) = true
                  AND provider->>'api_key_encrypted' IS NOT NULL
                ORDER BY provider->>'configured_at' DESC NULLS LAST
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id},
        )
        row = result.one_or_none()
        if row is None:
            return None
        default_model = row.default_model or await self._get_system_default_model() or "gpt-5-mini"
        return ResolvedAIConfig(
            provider=row.provider,
            api_key=decrypt_api_key(row.api_key_encrypted),
            default_model=default_model,
        )

    async def _get_system_default_model(self) -> str | None:
        result = await self.connection.execute(
            text("SELECT ai_default_model FROM system_settings WHERE id = 1 LIMIT 1")
        )
        row = result.one_or_none()
        return row.ai_default_model if row else None

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
