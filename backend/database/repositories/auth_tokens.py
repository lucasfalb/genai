import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


@dataclass(frozen=True)
class AuthActionTokenRecord:
    id: UUID
    user_id: UUID
    tenant_id: UUID | None
    token_hash: str
    token_type: str
    expires_at: datetime
    consumed_at: datetime | None
    created_at: datetime


class AuthActionTokenRepository:
    VALID_TYPES = {"account_activation", "password_reset", "tenant_invitation"}

    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        token_type: str,
        expires_at: datetime,
        tenant_id: UUID | None = None,
    ) -> AuthActionTokenRecord:
        if token_type not in self.VALID_TYPES:
            raise ValueError(f"Invalid token_type: {token_type}")
        result = await self.connection.execute(
            text(
                """
                INSERT INTO auth_action_tokens (user_id, tenant_id, token_hash, token_type, expires_at)
                VALUES (:user_id, :tenant_id, :token_hash, :token_type, :expires_at)
                RETURNING id, user_id, tenant_id, token_hash, token_type, expires_at, consumed_at, created_at
                """
            ),
            {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "token_hash": token_hash,
                "token_type": token_type,
                "expires_at": expires_at,
            },
        )
        return _token_from_row(result.one())

    async def consume(self, *, token_hash: str, token_type: str | None = None) -> AuthActionTokenRecord | None:
        if token_type is not None and token_type not in self.VALID_TYPES:
            raise ValueError(f"Invalid token_type: {token_type}")
        result = await self.connection.execute(
            text(
                """
                UPDATE auth_action_tokens
                SET consumed_at = now()
                WHERE token_hash = :token_hash
                AND (CAST(:token_type AS text) IS NULL OR token_type = CAST(:token_type AS text))
                AND consumed_at IS NULL
                AND expires_at > now()
                RETURNING id, user_id, tenant_id, token_hash, token_type, expires_at, consumed_at, created_at
                """
            ),
            {"token_hash": token_hash, "token_type": token_type},
        )
        row = result.one_or_none()
        return None if row is None else _token_from_row(row)

    async def invalidate_all_for_user(self, *, user_id: UUID, token_type: str) -> int:
        result = await self.connection.execute(
            text(
                """
                UPDATE auth_action_tokens
                SET consumed_at = now()
                WHERE user_id = :user_id
                AND token_type = :token_type
                AND consumed_at IS NULL
                """
            ),
            {"user_id": user_id, "token_type": token_type},
        )
        return result.rowcount


def _token_from_row(row) -> AuthActionTokenRecord:
        return AuthActionTokenRecord(
        id=row.id,
        user_id=row.user_id,
        tenant_id=row.tenant_id,
        token_hash=row.token_hash,
        token_type=row.token_type,
        expires_at=row.expires_at,
        consumed_at=row.consumed_at,
        created_at=row.created_at,
    )


@dataclass(frozen=True)
class EmailEventRecord:
    id: UUID
    template_id: UUID
    recipient_email: str
    payload: dict
    status: str
    attempts: int
    last_attempt_at: datetime | None
    sent_at: datetime | None
    error_message: str | None
    created_at: datetime


class EmailEventRepository:
    SENSITIVE_PAYLOAD_KEYS = {"password", "password_hash", "token_hash", "secret", "api_key", "apikey", "authorization"}

    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def create(
        self,
        *,
        template_id: UUID,
        recipient_email: str,
        payload: dict,
    ) -> EmailEventRecord:
        _reject_sensitive_payload(payload)
        result = await self.connection.execute(
            text(
                """
                INSERT INTO email_events (template_id, recipient_email, payload)
                VALUES (:template_id, :recipient_email, CAST(:payload AS jsonb))
                RETURNING id, template_id, recipient_email, payload, status, attempts,
                          last_attempt_at, sent_at, error_message, created_at
                """
            ),
            {
                "template_id": template_id,
                "recipient_email": recipient_email,
                "payload": json.dumps(payload),
            },
        )
        return _event_from_row(result.one())

    async def mark_sent(self, *, event_id: UUID) -> EmailEventRecord | None:
        result = await self.connection.execute(
            text(
                """
                UPDATE email_events
                SET status = 'sent', sent_at = now(), last_attempt_at = now(), attempts = attempts + 1
                WHERE id = :event_id
                RETURNING id, template_id, recipient_email, payload, status, attempts,
                          last_attempt_at, sent_at, error_message, created_at
                """
            ),
            {"event_id": event_id},
        )
        row = result.one_or_none()
        return None if row is None else _event_from_row(row)

    async def mark_failed(self, *, event_id: UUID, error_message: str) -> EmailEventRecord | None:
        result = await self.connection.execute(
            text(
                """
                UPDATE email_events
                SET status = 'failed', error_message = :error_message,
                    last_attempt_at = now(), attempts = attempts + 1
                WHERE id = :event_id
                RETURNING id, template_id, recipient_email, payload, status, attempts,
                          last_attempt_at, sent_at, error_message, created_at
                """
            ),
            {"event_id": event_id, "error_message": error_message},
        )
        row = result.one_or_none()
        return None if row is None else _event_from_row(row)

    async def list_pending(self, *, limit: int = 100) -> list[EmailEventRecord]:
        result = await self.connection.execute(
            text(
                """
                SELECT id, template_id, recipient_email, payload, status, attempts,
                       last_attempt_at, sent_at, error_message, created_at
                FROM email_events
                WHERE status = 'pending'
                ORDER BY created_at
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
        return [_event_from_row(row) for row in result.fetchall()]


def _event_from_row(row) -> EmailEventRecord:
    return EmailEventRecord(
        id=row.id,
        template_id=row.template_id,
        recipient_email=row.recipient_email,
        payload=row.payload if isinstance(row.payload, dict) else json.loads(row.payload),
        status=row.status,
        attempts=row.attempts,
        last_attempt_at=row.last_attempt_at,
        sent_at=row.sent_at,
        error_message=row.error_message,
        created_at=row.created_at,
    )


def _reject_sensitive_payload(payload: dict) -> None:
    for key, value in payload.items():
        normalized = key.lower().replace("-", "_")
        if normalized in EmailEventRepository.SENSITIVE_PAYLOAD_KEYS:
            raise ValueError(f"Sensitive email event payload key is not allowed: {key}")
        if isinstance(value, dict):
            _reject_sensitive_payload(value)
