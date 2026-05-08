from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


@dataclass(frozen=True)
class TenantMemberRecord:
    user_id: UUID
    email: str
    name: str | None
    role: str
    status: str


class MembershipAdminRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def list_members(
        self, *, tenant_id: UUID, include_superadmins: bool = False
    ) -> list[TenantMemberRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT u.id AS user_id, u.email, u.name, m.role, m.status
                FROM memberships m
                JOIN users u ON u.id = m.user_id
                WHERE m.tenant_id = :tenant_id
                  AND (:include_superadmins OR u.is_superadmin = false)
                ORDER BY u.email
                """
            ),
            {"tenant_id": tenant_id, "include_superadmins": include_superadmins},
        )
        return [_member_from_row(row) for row in result.fetchall()]

    async def get_member(
        self, *, tenant_id: UUID, user_id: UUID, include_superadmins: bool = False
    ) -> TenantMemberRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT u.id AS user_id, u.email, u.name, m.role, m.status
                FROM memberships m
                JOIN users u ON u.id = m.user_id
                WHERE m.tenant_id = :tenant_id
                  AND m.user_id = :user_id
                  AND (:include_superadmins OR u.is_superadmin = false)
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "include_superadmins": include_superadmins,
            },
        )
        row = result.one_or_none()
        return None if row is None else _member_from_row(row)

    async def update_member(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        role: str | None = None,
        status: str | None = None,
        include_superadmins: bool = False,
    ) -> TenantMemberRecord | None:
        result = await self.connection.execute(
            text(
                """
                UPDATE memberships m
                SET
                  role = COALESCE(:role, m.role),
                  status = COALESCE(:status, m.status)
                FROM users u
                WHERE u.id = m.user_id
                  AND m.tenant_id = :tenant_id
                  AND m.user_id = :user_id
                  AND (:include_superadmins OR u.is_superadmin = false)
                RETURNING u.id AS user_id, u.email, u.name, m.role, m.status
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "role": role,
                "status": status,
                "include_superadmins": include_superadmins,
            },
        )
        row = result.one_or_none()
        return None if row is None else _member_from_row(row)

    async def delete_member(
        self, *, tenant_id: UUID, user_id: UUID, include_superadmins: bool = False
    ) -> TenantMemberRecord | None:
        existing = await self.get_member(
            tenant_id=tenant_id, user_id=user_id, include_superadmins=include_superadmins
        )
        if existing is None:
            return None
        await self.connection.execute(
            text(
                """
                DELETE FROM memberships
                WHERE tenant_id = :tenant_id
                  AND user_id = :user_id
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id},
        )
        return existing

    async def upsert_active_member(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        role: str,
        invited_by: UUID | None,
        include_superadmins: bool = False,
    ) -> TenantMemberRecord | None:
        result = await self.connection.execute(
            text(
                """
                INSERT INTO memberships (user_id, tenant_id, role, status, invited_by)
                VALUES (:user_id, :tenant_id, :role, 'active', :invited_by)
                ON CONFLICT (user_id, tenant_id)
                DO UPDATE SET
                  role = EXCLUDED.role,
                  status = 'active',
                  invited_by = EXCLUDED.invited_by
                RETURNING user_id
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id, "role": role, "invited_by": invited_by},
        )
        if result.one_or_none() is None:
            return None
        return await self.get_member(
            tenant_id=tenant_id, user_id=user_id, include_superadmins=include_superadmins
        )


def _member_from_row(row) -> TenantMemberRecord:
    return TenantMemberRecord(
        user_id=row.user_id,
        email=row.email,
        name=row.name,
        role=row.role,
        status=row.status,
    )
