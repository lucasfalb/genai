from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import psycopg
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.security import hash_password, hash_token
from conftest import api_data, api_error


async def test_forgot_and_reset_password_revokes_refresh_tokens(db_connection: psycopg.Connection) -> None:
    suffix = uuid4().hex
    email = f"reset-{suffix}@example.com"
    old_password = "correct-password"
    new_password = "new-correct-password"
    _seed_active_member(db_connection, suffix, email=email, password=old_password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": old_password},
        )
        old_refresh_token = api_data(login_response)["refresh_token"]
        missing_response = await client.post(
            "/api/v1/auth/password/forgot",
            json={"email": f"missing-{suffix}@example.com"},
        )
        forgot_response = await client.post("/api/v1/auth/password/forgot", json={"email": email})

    assert missing_response.status_code == 200
    assert forgot_response.status_code == 200
    assert api_data(forgot_response)["message"].startswith("If the account")

    token = _latest_password_reset_token(db_connection, email)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        reset_response = await client.post(
            "/api/v1/auth/password/reset",
            json={"token": token, "new_password": new_password},
        )
        old_refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh_token},
        )
        old_password_login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": old_password},
        )
        new_password_login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": new_password},
        )

    assert reset_response.status_code == 200
    assert api_data(reset_response)["message"] == "Password reset successfully."
    assert old_refresh_response.status_code == 401
    assert old_password_login.status_code == 401
    assert new_password_login.status_code == 200
    assert api_data(new_password_login)["refresh_token"]
    assert _latest_email_template_slug(db_connection, email) == "password_changed"


async def test_reset_password_rejects_reused_and_expired_tokens(db_connection: psycopg.Connection) -> None:
    suffix = uuid4().hex
    email = f"reset-reuse-{suffix}@example.com"
    _seed_active_member(db_connection, suffix, email=email, password="correct-password")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/auth/password/forgot", json={"email": email})

    token = _latest_password_reset_token(db_connection, email)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first_response = await client.post(
            "/api/v1/auth/password/reset",
            json={"token": token, "new_password": "new-correct-password"},
        )
        reused_response = await client.post(
            "/api/v1/auth/password/reset",
            json={"token": token, "new_password": "another-correct-password"},
        )

    assert first_response.status_code == 200
    assert reused_response.status_code == 400
    assert api_error(reused_response)["code"] == "INVALID_OR_EXPIRED_PASSWORD_RESET_TOKEN"

    expired_token = f"expired-reset-{suffix}"
    _insert_expired_reset_token(db_connection, email, expired_token)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        expired_response = await client.post(
            "/api/v1/auth/password/reset",
            json={"token": expired_token, "new_password": "expired-correct-password"},
        )

    assert expired_response.status_code == 400


async def test_change_password_requires_current_password_and_revokes_refresh_tokens(
    db_connection: psycopg.Connection,
) -> None:
    suffix = uuid4().hex
    email = f"change-{suffix}@example.com"
    old_password = "correct-password"
    new_password = "changed-correct-password"
    _seed_active_member(db_connection, suffix, email=email, password=old_password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": old_password},
        )
        tokens = api_data(login_response)
        wrong_response = await client.post(
            "/api/v1/auth/password/change",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={"current_password": "wrong-password", "new_password": new_password},
        )
        change_response = await client.post(
            "/api/v1/auth/password/change",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={"current_password": old_password, "new_password": new_password},
        )
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        login_with_new_password = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": new_password},
        )

    assert wrong_response.status_code == 403
    assert api_error(wrong_response)["code"] == "CURRENT_PASSWORD_IS_INVALID"
    assert change_response.status_code == 200
    assert api_data(change_response)["message"] == "Password changed successfully."
    assert refresh_response.status_code == 401
    assert login_with_new_password.status_code == 200


def _seed_active_member(db_connection: psycopg.Connection, suffix: str, *, email: str, password: str) -> None:
    with db_connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tenants (slug, name) VALUES (%s, 'Password Tenant') RETURNING id",
            (f"password-tenant-{suffix}",),
        )
        tenant_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status)
            VALUES (%s, 'Password User', %s, 'active')
            RETURNING id
            """,
            (email, hash_password(password)),
        )
        user_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO memberships (user_id, tenant_id, role, status)
            VALUES (%s, %s, 'tenant_admin', 'active')
            """,
            (user_id, tenant_id),
        )
        db_connection.commit()


def _latest_password_reset_token(db_connection: psycopg.Connection, email: str) -> str:
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT ee.payload->>'reset_url'
            FROM email_events ee
            JOIN email_templates et ON et.id = ee.template_id
            WHERE ee.recipient_email = %s AND et.slug = 'password_reset'
            ORDER BY ee.created_at DESC
            LIMIT 1
            """,
            (email,),
        )
        reset_url = cursor.fetchone()[0]
    return parse_qs(urlparse(reset_url).query)["token"][0]


def _latest_email_template_slug(db_connection: psycopg.Connection, email: str) -> str:
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT et.slug
            FROM email_events ee
            JOIN email_templates et ON et.id = ee.template_id
            WHERE ee.recipient_email = %s
            ORDER BY ee.created_at DESC
            LIMIT 1
            """,
            (email,),
        )
        return cursor.fetchone()[0]


def _insert_expired_reset_token(db_connection: psycopg.Connection, email: str, token: str) -> None:
    with db_connection.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO auth_action_tokens (user_id, token_hash, token_type, expires_at)
            VALUES (%s, %s, 'password_reset', %s)
            """,
            (user_id, hash_token(token), datetime.now(UTC) - timedelta(minutes=1)),
        )
        db_connection.commit()
