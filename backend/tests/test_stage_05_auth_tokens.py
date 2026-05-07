import hashlib
import secrets
from datetime import UTC, timedelta, datetime

import psycopg
import pytest

from app.config import settings


def psycopg_url() -> str:
    return settings.test_database_url.replace("postgresql+psycopg://", "postgresql://")


@pytest.fixture()
def db():
    with psycopg.connect(psycopg_url(), autocommit=False) as conn:
        yield conn
        conn.rollback()


def _insert_user(cursor, email="token-user@example.com", status="pending"):
    cursor.execute(
        "INSERT INTO users (email, name, status) VALUES (%s, 'Token User', %s) RETURNING id",
        (email, status),
    )
    return cursor.fetchone()[0]


def _insert_email_template(cursor):
    cursor.execute(
        """
        INSERT INTO email_templates (slug, name, subject_template, body_template, variables_schema)
        VALUES ('account_activation', 'Activation', 'Activate', '<p>Click {{activation_url}}</p>', '{}')
        ON CONFLICT (slug) DO NOTHING
        RETURNING id
        """
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("SELECT id FROM email_templates WHERE slug = 'account_activation'")
    return cursor.fetchone()[0]


class TestAuthActionTokens:
    def test_create_and_consume_token(self, db):
        with db.cursor() as cur:
            user_id = _insert_user(cur)
            token_raw = secrets.token_urlsafe(48)
            token_hash = hashlib.sha256(token_raw.encode()).hexdigest()
            expires_at = datetime.now(UTC) + timedelta(minutes=15)

            cur.execute(
                """
                INSERT INTO auth_action_tokens (user_id, token_hash, token_type, expires_at)
                VALUES (%s, %s, 'account_activation', %s)
                RETURNING id, token_type, consumed_at
                """,
                (user_id, token_hash, expires_at),
            )
            row = cur.fetchone()
            assert row[1] == "account_activation"
            assert row[2] is None
            token_id = row[0]

            cur.execute(
                """
                UPDATE auth_action_tokens SET consumed_at = now()
                WHERE token_hash = %s AND consumed_at IS NULL AND expires_at > now()
                RETURNING id
                """,
                (token_hash,),
            )
            assert cur.fetchone()[0] == token_id

    def test_consumed_token_cannot_be_reused(self, db):
        with db.cursor() as cur:
            user_id = _insert_user(cur, email="reuse@example.com")
            token_raw = secrets.token_urlsafe(48)
            token_hash = hashlib.sha256(token_raw.encode()).hexdigest()
            expires_at = datetime.now(UTC) + timedelta(minutes=15)

            cur.execute(
                "INSERT INTO auth_action_tokens (user_id, token_hash, token_type, expires_at) VALUES (%s, %s, 'account_activation', %s)",
                (user_id, token_hash, expires_at),
            )

            cur.execute(
                "UPDATE auth_action_tokens SET consumed_at = now() WHERE token_hash = %s AND consumed_at IS NULL AND expires_at > now()",
                (token_hash,),
            )
            assert cur.rowcount == 1

            cur.execute(
                "UPDATE auth_action_tokens SET consumed_at = now() WHERE token_hash = %s AND consumed_at IS NULL AND expires_at > now()",
                (token_hash,),
            )
            assert cur.rowcount == 0

    def test_expired_token_is_rejected(self, db):
        with db.cursor() as cur:
            user_id = _insert_user(cur, email="expired@example.com")
            token_raw = secrets.token_urlsafe(48)
            token_hash = hashlib.sha256(token_raw.encode()).hexdigest()
            expires_at = datetime.now(UTC) - timedelta(minutes=1)

            cur.execute(
                "INSERT INTO auth_action_tokens (user_id, token_hash, token_type, expires_at) VALUES (%s, %s, 'password_reset', %s)",
                (user_id, token_hash, expires_at),
            )

            cur.execute(
                "UPDATE auth_action_tokens SET consumed_at = now() WHERE token_hash = %s AND consumed_at IS NULL AND expires_at > now()",
                (token_hash,),
            )
            assert cur.rowcount == 0

    def test_token_hash_only_no_plaintext(self, db):
        with db.cursor() as cur:
            user_id = _insert_user(cur, email="no-plain@example.com")
            token_raw = secrets.token_urlsafe(48)
            token_hash = hashlib.sha256(token_raw.encode()).hexdigest()
            expires_at = datetime.now(UTC) + timedelta(minutes=15)

            cur.execute(
                "INSERT INTO auth_action_tokens (user_id, token_hash, token_type, expires_at) VALUES (%s, %s, 'password_reset', %s)",
                (user_id, token_hash, expires_at),
            )

            cur.execute("SELECT token_hash FROM auth_action_tokens WHERE user_id = %s", (user_id,))
            stored = cur.fetchone()[0]
            assert stored == token_hash
            assert token_raw not in stored

    def test_invalidate_all_for_user_type(self, db):
        with db.cursor() as cur:
            user_id = _insert_user(cur, email="invalidate@example.com")
            expires_at = datetime.now(UTC) + timedelta(minutes=15)

            for i in range(3):
                h = hashlib.sha256(secrets.token_urlsafe(48).encode()).hexdigest()
                cur.execute(
                    "INSERT INTO auth_action_tokens (user_id, token_hash, token_type, expires_at) VALUES (%s, %s, 'password_reset', %s)",
                    (user_id, h, expires_at),
                )

            cur.execute(
                "UPDATE auth_action_tokens SET consumed_at = now() WHERE user_id = %s AND token_type = 'password_reset' AND consumed_at IS NULL",
                (user_id,),
            )
            assert cur.rowcount == 3

            cur.execute(
                "SELECT count(*) FROM auth_action_tokens WHERE user_id = %s AND token_type = 'password_reset' AND consumed_at IS NOT NULL",
                (user_id,),
            )
            assert cur.fetchone()[0] == 3


class TestEmailEvents:
    def test_create_email_event(self, db):
        with db.cursor() as cur:
            template_id = _insert_email_template(cur)
            cur.execute(
                "INSERT INTO email_events (template_id, recipient_email, payload) VALUES (%s, 'user@example.com', %s) RETURNING id, status, attempts",
                (template_id, '{"activation_url": "https://app/activate?token=abc"}'),
            )
            row = cur.fetchone()
            assert row[1] == "pending"
            assert row[2] == 0

    def test_mark_sent(self, db):
        with db.cursor() as cur:
            template_id = _insert_email_template(cur)
            cur.execute(
                "INSERT INTO email_events (template_id, recipient_email, payload) VALUES (%s, 'sent@example.com', '{}') RETURNING id",
                (template_id,),
            )
            event_id = cur.fetchone()[0]

            cur.execute(
                """
                UPDATE email_events
                SET status = 'sent', sent_at = now(), last_attempt_at = now(), attempts = attempts + 1
                WHERE id = %s
                RETURNING status, sent_at, attempts
                """,
                (event_id,),
            )
            row = cur.fetchone()
            assert row[0] == "sent"
            assert row[1] is not None
            assert row[2] == 1

    def test_mark_failed(self, db):
        with db.cursor() as cur:
            template_id = _insert_email_template(cur)
            cur.execute(
                "INSERT INTO email_events (template_id, recipient_email, payload) VALUES (%s, 'fail@example.com', '{}') RETURNING id",
                (template_id,),
            )
            event_id = cur.fetchone()[0]

            cur.execute(
                """
                UPDATE email_events
                SET status = 'failed', error_message = 'SMTP timeout',
                    last_attempt_at = now(), attempts = attempts + 1
                WHERE id = %s
                RETURNING status, error_message, attempts
                """,
                (event_id,),
            )
            row = cur.fetchone()
            assert row[0] == "failed"
            assert row[1] == "SMTP timeout"
            assert row[2] == 1

    def test_payload_no_secrets(self, db):
        with db.cursor() as cur:
            template_id = _insert_email_template(cur)
            payload = '{"user_name": "John", "activation_url": "https://app/activate?token=abc"}'
            cur.execute(
                "INSERT INTO email_events (template_id, recipient_email, payload) VALUES (%s, 'safe@example.com', %s) RETURNING payload",
                (template_id, payload),
            )
            stored = cur.fetchone()[0]
            stored_str = str(stored)
            assert "password" not in stored_str.lower()
            assert "secret" not in stored_str.lower()
