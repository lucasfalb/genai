from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import psycopg
from httpx import ASGITransport, AsyncClient

import api.v1.tenant_invitations as invitations_api
from app.main import app
from app.security import create_access_token, hash_token
from conftest import api_data, api_error


async def test_tenant_admin_invites_validates_and_accepts_new_user(
    db_connection: psycopg.Connection,
    monkeypatch,
) -> None:
    setup = _seed_invitation_tenant(db_connection, uuid4().hex)
    fake_redis = _FakeRedis()
    monkeypatch.setattr(invitations_api, "redis_client", fake_redis)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])
    invitee_email = f"invitee-{uuid4().hex}@example.com"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_response = await client.post(
            "/api/v1/tenant/invitations",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"email": invitee_email, "role": "member"},
        )
        list_response = await client.get(
            "/api/v1/tenant/invitations",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    assert create_response.status_code == 201
    invitation = api_data(create_response)
    assert invitation["email"] == invitee_email
    assert invitation["role"] == "member"
    assert invitation["status"] == "pending"
    assert invitee_email in {item["email"] for item in api_data(list_response)}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resend_response = await client.post(
            f"/api/v1/tenant/invitations/{invitation['id']}/resend",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )
    assert resend_response.status_code == 200

    invitation_token = _latest_invitation_token(db_connection, invitee_email)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        validate_response = await client.post("/api/v1/invitations/validate", json={"token": invitation_token})
        accept_response = await client.post(
            "/api/v1/invitations/accept",
            json={
                "token": invitation_token,
                "email": invitee_email,
                "name": "Invited User",
                "password": "InvitePassword123!",
            },
        )
        reuse_response = await client.post(
            "/api/v1/invitations/accept",
            json={"token": invitation_token, "email": invitee_email, "password": "InvitePassword123!"},
        )

    assert validate_response.status_code == 200
    assert api_data(validate_response)["tenant_id"] == str(setup["tenant_id"])
    assert accept_response.status_code == 200
    accepted = api_data(accept_response)
    assert accepted["email"] == invitee_email
    assert accepted["tenant_id"] == str(setup["tenant_id"])
    assert accepted["role"] == "member"
    assert accepted["membership_status"] == "active"
    assert reuse_response.status_code == 400
    assert api_error(reuse_response)["code"] == "INVALID_OR_EXPIRED_TENANT_INVITATION"

    with db_connection.cursor() as cursor:
        cursor.execute("SELECT id, status FROM users WHERE email = %s", (invitee_email,))
        user_id, user_status = cursor.fetchone()
        assert user_status == "active"
        cursor.execute(
            "SELECT role, status FROM memberships WHERE tenant_id = %s AND user_id = %s",
            (setup["tenant_id"], user_id),
        )
        assert cursor.fetchone() == ("member", "active")
        cursor.execute("SELECT status, accepted_at FROM invitations WHERE id = %s", (invitation["id"],))
        invite_status, accepted_at = cursor.fetchone()
        assert invite_status == "accepted"
        assert accepted_at is not None
        cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(setup["tenant_id"]),))
        cursor.execute(
            """
            SELECT count(*)
            FROM resource_versions
            WHERE tenant_id = %s AND resource IN ('invitations', 'memberships')
            """,
            (setup["tenant_id"],),
        )
        assert cursor.fetchone()[0] >= 2
        cursor.execute("RESET app.current_tenant_id")
    assert f"membership:{accepted['user_id']}:{setup['tenant_id']}" in fake_redis.deleted


async def test_cancelled_expired_or_wrong_email_invitation_cannot_be_accepted(
    db_connection: psycopg.Connection,
) -> None:
    setup = _seed_invitation_tenant(db_connection, uuid4().hex)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])
    cancelled_email = f"cancelled-{uuid4().hex}@example.com"
    expired_email = f"expired-{uuid4().hex}@example.com"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_response = await client.post(
            "/api/v1/tenant/invitations",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"email": cancelled_email, "role": "viewer"},
        )
        invitation_id = api_data(create_response)["id"]
        cancel_response = await client.delete(
            f"/api/v1/tenant/invitations/{invitation_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    assert cancel_response.status_code == 200
    cancelled_token = _latest_invitation_token(db_connection, cancelled_email)
    expired_token = "expired-invitation-token"
    wrong_email = f"wrong-{uuid4().hex}@example.com"
    _insert_expired_invitation(db_connection, setup, expired_email, expired_token)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        wrong_create = await client.post(
            "/api/v1/tenant/invitations",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"email": wrong_email, "role": "member"},
        )
    assert wrong_create.status_code == 201
    wrong_token = _latest_invitation_token(db_connection, wrong_email)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        cancelled_accept = await client.post(
            "/api/v1/invitations/accept",
            json={"token": cancelled_token, "email": cancelled_email, "password": "InvitePassword123!"},
        )
        expired_validate = await client.post("/api/v1/invitations/validate", json={"token": expired_token})
        wrong_email_accept = await client.post(
            "/api/v1/invitations/accept",
            json={"token": wrong_token, "email": "wrong@example.com", "password": "InvitePassword123!"},
        )

    assert cancelled_accept.status_code == 400
    assert expired_validate.status_code == 400
    assert wrong_email_accept.status_code == 400


async def test_superadmin_invites_without_visible_membership_and_member_cannot_invite(
    db_connection: psycopg.Connection,
) -> None:
    setup = _seed_invitation_tenant(db_connection, uuid4().hex)
    superadmin_token = create_access_token(
        user_id=setup["superadmin_id"],
        email=setup["superadmin_email"],
        is_superadmin=True,
    )
    member_token = create_access_token(user_id=setup["member_id"], email=setup["member_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        superadmin_response = await client.post(
            "/api/v1/tenant/invitations",
            headers={"Authorization": f"Bearer {superadmin_token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"email": f"super-invite-{uuid4().hex}@example.com", "role": "tenant_admin"},
        )
        list_response = await client.get(
            "/api/v1/tenant/members",
            headers={"Authorization": f"Bearer {superadmin_token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )
        member_response = await client.post(
            "/api/v1/tenant/invitations",
            headers={"Authorization": f"Bearer {member_token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"email": f"blocked-{uuid4().hex}@example.com", "role": "member"},
        )

    assert superadmin_response.status_code == 201
    assert member_response.status_code == 403
    assert str(setup["superadmin_id"]) not in {item["user_id"] for item in api_data(list_response)}

    with db_connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(setup["tenant_id"]),))
        cursor.execute(
            """
            SELECT actor_type, actor_role
            FROM audit_logs
            WHERE tenant_id = %s AND user_id = %s AND resource = 'invitations'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (setup["tenant_id"], setup["superadmin_id"]),
        )
        assert cursor.fetchone() == ("superadmin", "superadmin")
        cursor.execute("RESET app.current_tenant_id")


def _seed_invitation_tenant(db_connection: psycopg.Connection, suffix: str) -> dict:
    with db_connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tenants (slug, name) VALUES (%s, 'Invitation Tenant') RETURNING id",
            (f"invitation-tenant-{suffix}",),
        )
        tenant_id = cursor.fetchone()[0]
        users = {}
        for key, role in (("admin", "tenant_admin"), ("member", "member")):
            email = f"{key}-{suffix}@example.com"
            cursor.execute(
                """
                INSERT INTO users (email, name, password_hash, status)
                VALUES (%s, %s, 'hash', 'active')
                RETURNING id
                """,
                (email, key.title()),
            )
            user_id = cursor.fetchone()[0]
            users[key] = {"id": user_id, "email": email}
            cursor.execute(
                """
                INSERT INTO memberships (user_id, tenant_id, role, status)
                VALUES (%s, %s, %s, 'active')
                """,
                (user_id, tenant_id, role),
            )
        superadmin_email = f"superadmin-{suffix}@example.com"
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status, is_superadmin)
            VALUES (%s, 'Superadmin', 'hash', 'active', true)
            RETURNING id
            """,
            (superadmin_email,),
        )
        superadmin_id = cursor.fetchone()[0]
        db_connection.commit()
    return {
        "tenant_id": tenant_id,
        "admin_id": users["admin"]["id"],
        "admin_email": users["admin"]["email"],
        "member_id": users["member"]["id"],
        "member_email": users["member"]["email"],
        "superadmin_id": superadmin_id,
        "superadmin_email": superadmin_email,
    }


def _latest_invitation_token(db_connection: psycopg.Connection, email: str) -> str:
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT ee.payload->>'invitation_url'
            FROM email_events ee
            JOIN email_templates et ON et.id = ee.template_id
            WHERE ee.recipient_email = %s AND et.slug = 'tenant_invitation'
            ORDER BY ee.created_at DESC
            LIMIT 1
            """,
            (email,),
        )
        invitation_url = cursor.fetchone()[0]
    query = parse_qs(urlparse(invitation_url).query)
    return query["token"][0]


def _insert_expired_invitation(db_connection: psycopg.Connection, setup: dict, email: str, token: str) -> None:
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO invitations (tenant_id, email, role, token_hash, status, invited_by, expires_at)
            VALUES (%s, %s, 'member', %s, 'pending', %s, %s)
            """,
            (
                setup["tenant_id"],
                email,
                hash_token(token),
                setup["admin_id"],
                datetime.now(UTC) - timedelta(minutes=1),
            ),
        )
        db_connection.commit()


class _FakeRedis:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def delete(self, key: str) -> None:
        self.deleted.append(key)
