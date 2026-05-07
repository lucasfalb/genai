from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


@dataclass(frozen=True)
class UserRecord:
    id: UUID
    email: str
    name: str | None
    password_hash: str | None
    is_superadmin: bool
    status: str


@dataclass(frozen=True)
class MembershipRecord:
    user_id: UUID
    tenant_id: UUID
    role: str
    status: str


@dataclass(frozen=True)
class TenantAccessRecord:
    tenant_id: UUID
    tenant_slug: str
    tenant_name: str
    role: str
    status: str


class UserRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def create_user(
        self,
        *,
        email: str,
        password_hash: str,
        name: str | None = None,
        status: str = "pending",
    ) -> UserRecord:
        result = await self.connection.execute(
            text(
                """
                INSERT INTO users (email, name, password_hash, status)
                VALUES (:email, :name, :password_hash, :status)
                RETURNING id, email, name, password_hash, is_superadmin, status
                """
            ),
            {"email": email.lower(), "name": name, "password_hash": password_hash, "status": status},
        )
        return _user_from_row(result.one())

    async def get_by_email(self, email: str) -> UserRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT id, email, name, password_hash, is_superadmin, status
                FROM users
                WHERE email = :email
                """
            ),
            {"email": email.lower()},
        )
        row = result.one_or_none()
        return None if row is None else _user_from_row(row)

    async def get_by_id(self, user_id: UUID) -> UserRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT id, email, name, password_hash, is_superadmin, status
                FROM users
                WHERE id = :user_id
                """
            ),
            {"user_id": user_id},
        )
        row = result.one_or_none()
        return None if row is None else _user_from_row(row)

    async def update_status(self, *, user_id: UUID, status: str) -> UserRecord | None:
        result = await self.connection.execute(
            text(
                """
                UPDATE users
                SET status = :status
                WHERE id = :user_id
                RETURNING id, email, name, password_hash, is_superadmin, status
                """
            ),
            {"user_id": user_id, "status": status},
        )
        row = result.one_or_none()
        return None if row is None else _user_from_row(row)

    async def update_password_hash(self, *, user_id: UUID, password_hash: str) -> UserRecord | None:
        result = await self.connection.execute(
            text(
                """
                UPDATE users
                SET password_hash = :password_hash
                WHERE id = :user_id
                RETURNING id, email, name, password_hash, is_superadmin, status
                """
            ),
            {"user_id": user_id, "password_hash": password_hash},
        )
        row = result.one_or_none()
        return None if row is None else _user_from_row(row)

    async def list_active_memberships(self, user_id: UUID) -> list[MembershipRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT user_id, tenant_id, role, status
                FROM memberships
                WHERE user_id = :user_id AND status = 'active'
                ORDER BY created_at
                """
            ),
            {"user_id": user_id},
        )
        return [_membership_from_row(row) for row in result.fetchall()]

    async def list_tenant_access(self, user_id: UUID) -> list[TenantAccessRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT t.id AS tenant_id, t.slug AS tenant_slug, t.name AS tenant_name, m.role, m.status
                FROM memberships m
                JOIN tenants t ON t.id = m.tenant_id
                WHERE m.user_id = :user_id
                  AND m.status = 'active'
                ORDER BY t.name, t.slug
                """
            ),
            {"user_id": user_id},
        )
        return [_tenant_access_from_row(row) for row in result.fetchall()]

    async def get_active_membership(self, user_id: UUID, tenant_id: UUID) -> MembershipRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT user_id, tenant_id, role, status
                FROM memberships
                WHERE user_id = :user_id
                  AND tenant_id = :tenant_id
                  AND status = 'active'
                """
            ),
            {"user_id": user_id, "tenant_id": tenant_id},
        )
        row = result.one_or_none()
        return None if row is None else _membership_from_row(row)

    async def tenant_exists(self, tenant_id: UUID) -> bool:
        result = await self.connection.execute(
            text("SELECT 1 FROM tenants WHERE id = :tenant_id"),
            {"tenant_id": tenant_id},
        )
        return result.one_or_none() is not None

    async def list_tenant_members(self, tenant_id: UUID) -> list[UserRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT u.id, u.email, u.name, u.password_hash, u.is_superadmin, u.status
                FROM users u
                JOIN memberships m ON m.user_id = u.id
                WHERE m.tenant_id = :tenant_id
                  AND m.status = 'active'
                  AND u.is_superadmin = false
                ORDER BY u.email
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [_user_from_row(row) for row in result.fetchall()]

    async def create_refresh_token(self, *, user_id: UUID, token_hash: str, expires_at: datetime) -> None:
        await self.connection.execute(
            text(
                """
                INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
                VALUES (:user_id, :token_hash, :expires_at)
                """
            ),
            {"user_id": user_id, "token_hash": token_hash, "expires_at": expires_at},
        )

    async def consume_refresh_token(self, *, token_hash: str) -> UserRecord | None:
        result = await self.connection.execute(
            text(
                """
                UPDATE refresh_tokens
                SET revoked_at = now()
                WHERE token_hash = :token_hash
                  AND revoked_at IS NULL
                  AND expires_at > now()
                RETURNING user_id
                """
            ),
            {"token_hash": token_hash},
        )
        row = result.one_or_none()
        if row is None:
            return None
        return await self.get_by_id(row.user_id)

    async def revoke_refresh_tokens(self, *, user_id: UUID) -> int:
        result = await self.connection.execute(
            text(
                """
                UPDATE refresh_tokens
                SET revoked_at = now()
                WHERE user_id = :user_id
                  AND revoked_at IS NULL
                """
            ),
            {"user_id": user_id},
        )
        return result.rowcount

    async def revoke_refresh_token(self, *, user_id: UUID, token_hash: str) -> int:
        result = await self.connection.execute(
            text(
                """
                UPDATE refresh_tokens
                SET revoked_at = now()
                WHERE user_id = :user_id
                  AND token_hash = :token_hash
                  AND revoked_at IS NULL
                """
            ),
            {"user_id": user_id, "token_hash": token_hash},
        )
        return result.rowcount


def _user_from_row(row) -> UserRecord:
    return UserRecord(
        id=row.id,
        email=row.email,
        name=row.name,
        password_hash=row.password_hash,
        is_superadmin=row.is_superadmin,
        status=row.status,
    )


def _membership_from_row(row) -> MembershipRecord:
    return MembershipRecord(user_id=row.user_id, tenant_id=row.tenant_id, role=row.role, status=row.status)


def _tenant_access_from_row(row) -> TenantAccessRecord:
    return TenantAccessRecord(
        tenant_id=row.tenant_id,
        tenant_slug=row.tenant_slug,
        tenant_name=row.tenant_name,
        role=row.role,
        status=row.status,
    )
