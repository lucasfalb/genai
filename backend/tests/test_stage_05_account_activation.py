from urllib.parse import parse_qs, urlparse
from uuid import uuid4
from datetime import UTC, datetime, timedelta

import psycopg
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.security import hash_token


async def test_register_queues_activation_and_confirm_activates_account(db_connection: psycopg.Connection) -> None:
    suffix = uuid4().hex
    email = f"activate-{suffix}@example.com"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "correct-password", "name": "Activation User"},
        )
        inactive_login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "correct-password"},
        )

    assert register_response.status_code == 201
    assert register_response.json()["status"] == "pending"
    assert inactive_login.status_code == 403

    token = _latest_activation_token(db_connection, email)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        confirm_response = await client.post("/api/v1/auth/activation/confirm", json={"token": token})
        reused_response = await client.post("/api/v1/auth/activation/confirm", json={"token": token})
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "correct-password"},
        )

    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "active"
    assert reused_response.status_code == 400
    assert login_response.status_code == 200
    assert login_response.json()["awaiting_assignment"] is True
    assert login_response.json()["access_token"] is None


async def test_activation_request_is_neutral_and_reissues_token(db_connection: psycopg.Connection) -> None:
    suffix = uuid4().hex
    email = f"reactivate-{suffix}@example.com"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "correct-password", "name": "Activation User"},
        )
        missing_response = await client.post(
            "/api/v1/auth/activation/request",
            json={"email": f"missing-{suffix}@example.com"},
        )
        request_response = await client.post("/api/v1/auth/activation/request", json={"email": email})

    assert missing_response.status_code == 200
    assert request_response.status_code == 200
    assert request_response.json()["message"].startswith("If the account")

    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT count(*)
            FROM auth_action_tokens aat
            JOIN users u ON u.id = aat.user_id
            WHERE u.email = %s AND aat.token_type = 'account_activation'
            """,
            (email,),
        )
        assert cursor.fetchone()[0] == 2
        cursor.execute(
            """
            SELECT count(*)
            FROM auth_action_tokens aat
            JOIN users u ON u.id = aat.user_id
            WHERE u.email = %s AND aat.token_type = 'account_activation' AND aat.consumed_at IS NULL
            """,
            (email,),
        )
        assert cursor.fetchone()[0] == 1


async def test_expired_activation_token_is_rejected(db_connection: psycopg.Connection) -> None:
    suffix = uuid4().hex
    email = f"expired-activation-{suffix}@example.com"
    token = f"expired-token-{suffix}"

    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status)
            VALUES (%s, 'Expired Activation', 'hash', 'pending')
            RETURNING id
            """,
            (email,),
        )
        user_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO auth_action_tokens (user_id, token_hash, token_type, expires_at)
            VALUES (%s, %s, 'account_activation', %s)
            """,
            (user_id, hash_token(token), datetime.now(UTC) - timedelta(minutes=1)),
        )
        db_connection.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/activation/confirm", json={"token": token})

    assert response.status_code == 400


def _latest_activation_token(db_connection: psycopg.Connection, email: str) -> str:
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT ee.payload->>'activation_url'
            FROM email_events ee
            JOIN email_templates et ON et.id = ee.template_id
            WHERE ee.recipient_email = %s AND et.slug = 'account_activation'
            ORDER BY ee.created_at DESC
            LIMIT 1
            """,
            (email,),
        )
        activation_url = cursor.fetchone()[0]
    return parse_qs(urlparse(activation_url).query)["token"][0]
