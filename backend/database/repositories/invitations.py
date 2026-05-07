from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


@dataclass(frozen=True)
class InvitationRecord:
    id: UUID
    tenant_id: UUID
    tenant_name: str | None
    email: str
    role: str
    token_hash: str
    status: str
    invited_by: UUID | None
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime


class InvitationRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def list_for_tenant(self, *, tenant_id: UUID) -> list[InvitationRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT i.id, i.tenant_id, t.name AS tenant_name, i.email, i.role, i.token_hash,
                       i.status, i.invited_by, i.expires_at, i.accepted_at, i.created_at
                FROM invitations i
                JOIN tenants t ON t.id = i.tenant_id
                WHERE i.tenant_id = :tenant_id
                ORDER BY i.created_at DESC
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [_invitation_from_row(row) for row in result.fetchall()]

    async def create_or_refresh(
        self,
        *,
        tenant_id: UUID,
        email: str,
        role: str,
        token_hash: str,
        invited_by: UUID,
        expires_at: datetime,
    ) -> InvitationRecord:
        result = await self.connection.execute(
            text(
                """
                INSERT INTO invitations (tenant_id, email, role, token_hash, status, invited_by, expires_at)
                VALUES (:tenant_id, :email, :role, :token_hash, 'pending', :invited_by, :expires_at)
                ON CONFLICT (tenant_id, email)
                DO UPDATE SET
                  role = EXCLUDED.role,
                  token_hash = EXCLUDED.token_hash,
                  status = 'pending',
                  invited_by = EXCLUDED.invited_by,
                  expires_at = EXCLUDED.expires_at,
                  accepted_at = NULL
                RETURNING id, tenant_id, NULL::text AS tenant_name, email, role, token_hash,
                          status, invited_by, expires_at, accepted_at, created_at
                """
            ),
            {
                "tenant_id": tenant_id,
                "email": email.lower(),
                "role": role,
                "token_hash": token_hash,
                "invited_by": invited_by,
                "expires_at": expires_at,
            },
        )
        return _invitation_from_row(result.one())

    async def get_by_id(self, *, tenant_id: UUID, invitation_id: UUID) -> InvitationRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT i.id, i.tenant_id, t.name AS tenant_name, i.email, i.role, i.token_hash,
                       i.status, i.invited_by, i.expires_at, i.accepted_at, i.created_at
                FROM invitations i
                JOIN tenants t ON t.id = i.tenant_id
                WHERE i.tenant_id = :tenant_id AND i.id = :invitation_id
                """
            ),
            {"tenant_id": tenant_id, "invitation_id": invitation_id},
        )
        row = result.one_or_none()
        return None if row is None else _invitation_from_row(row)

    async def get_by_token_hash(self, *, token_hash: str) -> InvitationRecord | None:
        result = await self.connection.execute(
            text(
                """
                SELECT i.id, i.tenant_id, t.name AS tenant_name, i.email, i.role, i.token_hash,
                       i.status, i.invited_by, i.expires_at, i.accepted_at, i.created_at
                FROM invitations i
                JOIN tenants t ON t.id = i.tenant_id
                WHERE i.token_hash = :token_hash
                """
            ),
            {"token_hash": token_hash},
        )
        row = result.one_or_none()
        return None if row is None else _invitation_from_row(row)

    async def cancel(self, *, tenant_id: UUID, invitation_id: UUID) -> InvitationRecord | None:
        result = await self.connection.execute(
            text(
                """
                UPDATE invitations
                SET status = 'cancelled'
                WHERE tenant_id = :tenant_id
                  AND id = :invitation_id
                  AND status = 'pending'
                  AND accepted_at IS NULL
                  AND expires_at > now()
                RETURNING id, tenant_id, NULL::text AS tenant_name, email, role, token_hash,
                          status, invited_by, expires_at, accepted_at, created_at
                """
            ),
            {"tenant_id": tenant_id, "invitation_id": invitation_id},
        )
        row = result.one_or_none()
        return None if row is None else _invitation_from_row(row)

    async def mark_accepted(self, *, invitation_id: UUID, token_hash: str) -> InvitationRecord | None:
        result = await self.connection.execute(
            text(
                """
                UPDATE invitations
                SET status = 'accepted', accepted_at = now()
                WHERE id = :invitation_id
                  AND token_hash = :token_hash
                  AND status = 'pending'
                  AND accepted_at IS NULL
                  AND expires_at > now()
                RETURNING id, tenant_id, NULL::text AS tenant_name, email, role, token_hash,
                          status, invited_by, expires_at, accepted_at, created_at
                """
            ),
            {"invitation_id": invitation_id, "token_hash": token_hash},
        )
        row = result.one_or_none()
        return None if row is None else _invitation_from_row(row)


def _invitation_from_row(row) -> InvitationRecord:
    return InvitationRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        tenant_name=row.tenant_name,
        email=row.email,
        role=row.role,
        token_hash=row.token_hash,
        status=row.status,
        invited_by=row.invited_by,
        expires_at=row.expires_at,
        accepted_at=row.accepted_at,
        created_at=row.created_at,
    )
