from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


@dataclass(frozen=True)
class PlatformAIConfigRecord:
    id: UUID
    provider: str
    base_url: str | None
    default_model: str
    is_active: bool


@dataclass(frozen=True)
class TenantAIConfigRecord:
    id: UUID
    tenant_id: UUID
    provider: str
    base_url: str | None
    default_model: str | None
    is_active: bool


class AIConfigRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    # ------------------------------------------------------------------
    # Platform config (superadmin)
    # ------------------------------------------------------------------

    async def get_platform_config(self) -> PlatformAIConfigRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT id, provider, base_url, default_model, is_active
                FROM platform_ai_configs
                WHERE is_active = true
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
        )
        row = result.one_or_none()
        return _platform_from_row(row) if row else None

    async def upsert_platform_config(
        self,
        *,
        provider: str,
        api_key_encrypted: str,
        default_model: str,
        base_url: str | None = None,
    ) -> PlatformAIConfigRecord:
        # Deactivate all existing, then insert new
        await self.connection.execute(
            text("UPDATE platform_ai_configs SET is_active = false")
        )
        result = await self.connection.execute(
            text(
                """
                INSERT INTO platform_ai_configs
                  (provider, base_url, api_key_encrypted, default_model, is_active)
                VALUES (:provider, :base_url, :api_key_encrypted, :default_model, true)
                RETURNING id, provider, base_url, default_model, is_active
                """
            ),
            {
                "provider": provider,
                "base_url": base_url,
                "api_key_encrypted": api_key_encrypted,
                "default_model": default_model,
            },
        )
        return _platform_from_row(result.one())

    async def delete_platform_config(self) -> bool:
        result = await self.connection.execute(
            text("DELETE FROM platform_ai_configs WHERE is_active = true RETURNING id")
        )
        return result.rowcount > 0

    # ------------------------------------------------------------------
    # Tenant config (tenant_admin)
    # ------------------------------------------------------------------

    async def get_tenant_config(self, *, tenant_id: UUID) -> TenantAIConfigRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT id, tenant_id, provider, base_url, default_model, is_active
                FROM tenant_ai_configs
                WHERE tenant_id = :tenant_id
                LIMIT 1
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
        provider: str,
        api_key_encrypted: str,
        default_model: str | None = None,
        base_url: str | None = None,
    ) -> TenantAIConfigRecord:
        result = await self.connection.execute(
            text(
                """
                INSERT INTO tenant_ai_configs
                  (tenant_id, provider, base_url, api_key_encrypted, default_model, is_active)
                VALUES (:tenant_id, :provider, :base_url, :api_key_encrypted, :default_model, true)
                ON CONFLICT (tenant_id) DO UPDATE SET
                  provider          = EXCLUDED.provider,
                  base_url          = EXCLUDED.base_url,
                  api_key_encrypted = EXCLUDED.api_key_encrypted,
                  default_model     = EXCLUDED.default_model,
                  is_active         = true,
                  updated_at        = now()
                RETURNING id, tenant_id, provider, base_url, default_model, is_active
                """
            ),
            {
                "tenant_id": tenant_id,
                "provider": provider,
                "base_url": base_url,
                "api_key_encrypted": api_key_encrypted,
                "default_model": default_model,
            },
        )
        return _tenant_from_row(result.one())

    async def delete_tenant_config(self, *, tenant_id: UUID) -> bool:
        result = await self.connection.execute(
            text("DELETE FROM tenant_ai_configs WHERE tenant_id = :tenant_id RETURNING id"),
            {"tenant_id": tenant_id},
        )
        return result.rowcount > 0


def _platform_from_row(row) -> PlatformAIConfigRecord:
    return PlatformAIConfigRecord(
        id=row.id,
        provider=row.provider,
        base_url=row.base_url,
        default_model=row.default_model,
        is_active=row.is_active,
    )


def _tenant_from_row(row) -> TenantAIConfigRecord:
    return TenantAIConfigRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        provider=row.provider,
        base_url=row.base_url,
        default_model=row.default_model,
        is_active=row.is_active,
    )
