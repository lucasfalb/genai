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

    async def list_members(self, *, tenant_id: UUID) -> list[TenantMemberRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT u.id AS user_id, u.email, u.name, m.role, m.status
                FROM memberships m
                JOIN users u ON u.id = m.user_id
                WHERE m.tenant_id = :tenant_id
                  AND u.is_superadmin = false
                ORDER BY u.email
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [_member_from_row(row) for row in result.fetchall()]

    async def get_member(self, *, tenant_id: UUID, user_id: UUID) -> TenantMemberRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT u.id AS user_id, u.email, u.name, m.role, m.status
                FROM memberships m
                JOIN users u ON u.id = m.user_id
                WHERE m.tenant_id = :tenant_id
                  AND m.user_id = :user_id
                  AND u.is_superadmin = false
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id},
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
                  AND u.is_superadmin = false
                RETURNING u.id AS user_id, u.email, u.name, m.role, m.status
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id, "role": role, "status": status},
        )
        row = result.one_or_none()
        return None if row is None else _member_from_row(row)

    async def delete_member(self, *, tenant_id: UUID, user_id: UUID) -> TenantMemberRecord | None:
        existing = await self.get_member(tenant_id=tenant_id, user_id=user_id)
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


def _member_from_row(row) -> TenantMemberRecord:
    return TenantMemberRecord(
        user_id=row.user_id,
        email=row.email,
        name=row.name,
        role=row.role,
        status=row.status,
    )
