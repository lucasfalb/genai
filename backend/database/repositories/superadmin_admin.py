import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


@dataclass(frozen=True)
class TenantAdminRecord:
    id: UUID
    slug: str
    name: str
    plan: str
    status: str
    settings: dict


@dataclass(frozen=True)
class UserAdminRecord:
    id: UUID
    email: str
    name: str | None
    status: str
    is_superadmin: bool


class SuperadminAdminRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def create_tenant(
        self,
        *,
        slug: str,
        name: str,
        plan: str,
        status: str,
        settings: dict,
    ) -> TenantAdminRecord:
        result = await self.connection.execute(
            text(
                """
                INSERT INTO tenants (slug, name, plan, status, settings)
                VALUES (:slug, :name, :plan, :status, CAST(:settings AS jsonb))
                RETURNING id, slug, name, plan, status, settings
                """
            ),
            {
                "slug": slug,
                "name": name,
                "plan": plan,
                "status": status,
                "settings": json.dumps(settings),
            },
        )
        return _tenant_from_row(result.one())

    async def list_tenants(self) -> list[TenantAdminRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT id, slug, name, plan, status, settings
                FROM tenants
                ORDER BY name, slug
                """
            )
        )
        return [_tenant_from_row(row) for row in result.fetchall()]

    async def get_tenant(self, tenant_id: UUID) -> TenantAdminRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT id, slug, name, plan, status, settings
                FROM tenants
                WHERE id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id},
        )
        row = result.one_or_none()
        return None if row is None else _tenant_from_row(row)

    async def update_tenant(
        self,
        *,
        tenant_id: UUID,
        name: str | None = None,
        plan: str | None = None,
        status: str | None = None,
        settings: dict | None = None,
    ) -> TenantAdminRecord | None:
        result = await self.connection.execute(
            text(
                """
                UPDATE tenants
                SET
                  name = COALESCE(:name, name),
                  plan = COALESCE(:plan, plan),
                  status = COALESCE(:status, status),
                  settings = COALESCE(CAST(:settings AS jsonb), settings),
                  updated_at = now()
                WHERE id = :tenant_id
                RETURNING id, slug, name, plan, status, settings
                """
            ),
            {
                "tenant_id": tenant_id,
                "name": name,
                "plan": plan,
                "status": status,
                "settings": None if settings is None else json.dumps(settings),
            },
        )
        row = result.one_or_none()
        return None if row is None else _tenant_from_row(row)

    async def list_users(
        self,
        *,
        query: str | None = None,
        status: str | None = None,
        is_superadmin: bool | None = None,
    ) -> list[UserAdminRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT id, email, name, status, is_superadmin
                FROM users
                WHERE (CAST(:query AS text) IS NULL OR email ILIKE :query_like OR name ILIKE :query_like)
                  AND (CAST(:status AS text) IS NULL OR status = CAST(:status AS text))
                  AND (CAST(:is_superadmin AS boolean) IS NULL OR is_superadmin = CAST(:is_superadmin AS boolean))
                ORDER BY email
                """
            ),
            {
                "query": query,
                "query_like": None if query is None else f"%{query}%",
                "status": status,
                "is_superadmin": is_superadmin,
            },
        )
        return [_user_from_row(row) for row in result.fetchall()]

    async def get_user(self, user_id: UUID) -> UserAdminRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT id, email, name, status, is_superadmin
                FROM users
                WHERE id = :user_id
                """
            ),
            {"user_id": user_id},
        )
        row = result.one_or_none()
        return None if row is None else _user_from_row(row)

    async def update_user(
        self,
        *,
        user_id: UUID,
        name: str | None = None,
        status: str | None = None,
        is_superadmin: bool | None = None,
    ) -> UserAdminRecord | None:
        result = await self.connection.execute(
            text(
                """
                UPDATE users
                SET
                  name = COALESCE(:name, name),
                  status = COALESCE(:status, status),
                  is_superadmin = COALESCE(CAST(:is_superadmin AS boolean), is_superadmin)
                WHERE id = :user_id
                RETURNING id, email, name, status, is_superadmin
                """
            ),
            {"user_id": user_id, "name": name, "status": status, "is_superadmin": is_superadmin},
        )
        row = result.one_or_none()
        return None if row is None else _user_from_row(row)


def _tenant_from_row(row) -> TenantAdminRecord:
    return TenantAdminRecord(
        id=row.id,
        slug=row.slug,
        name=row.name,
        plan=row.plan,
        status=row.status,
        settings=row.settings if isinstance(row.settings, dict) else json.loads(row.settings),
    )


def _user_from_row(row) -> UserAdminRecord:
    return UserAdminRecord(
        id=row.id,
        email=row.email,
        name=row.name,
        status=row.status,
        is_superadmin=row.is_superadmin,
    )
