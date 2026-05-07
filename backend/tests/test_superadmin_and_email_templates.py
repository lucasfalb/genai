from contextlib import asynccontextmanager
from uuid import uuid4

import psycopg
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.rbac import Permission
from app.security import create_access_token, hash_password
from conftest import api_data
from database.connection import engine
from database.repositories.users import UserRepository
from dependencies.auth import require_permission


async def test_superadmin_login_issues_tokens_without_membership(db_connection: psycopg.Connection) -> None:
    suffix = uuid4().hex
    email = f"superadmin-{suffix}@example.com"
    password = "correct-password"

    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status, is_superadmin)
            VALUES (%s, 'Super Admin', %s, 'active', true)
            """,
            (email, hash_password(password)),
        )
        db_connection.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )

    body = api_data(response)
    assert response.status_code == 200
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["awaiting_assignment"] is False
    assert body["memberships"] == []


async def test_superadmin_has_tenant_control_without_membership_and_is_not_tenant_member(
    db_connection: psycopg.Connection,
) -> None:
    suffix = uuid4().hex
    test_app = FastAPI()

    @test_app.get("/protected")
    async def protected(_=Depends(require_permission(Permission.INVITE_MEMBERS))) -> dict[str, bool]:
        return {"ok": True}

    with db_connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tenants (slug, name) VALUES (%s, 'Tenant With Members') RETURNING id",
            (f"tenant-members-{suffix}",),
        )
        tenant_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status, is_superadmin)
            VALUES (%s, 'Super Admin', 'hash', 'active', true)
            RETURNING id
            """,
            (f"platform-admin-{suffix}@example.com",),
        )
        superadmin_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status)
            VALUES (%s, 'Tenant Member', 'hash', 'active')
            RETURNING id
            """,
            (f"tenant-member-{suffix}@example.com",),
        )
        member_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO memberships (user_id, tenant_id, role, status)
            VALUES (%s, %s, 'member', 'active')
            """,
            (member_id, tenant_id),
        )
        db_connection.commit()

    token = create_access_token(
        user_id=superadmin_id,
        email=f"platform-admin-{suffix}@example.com",
        is_superadmin=True,
    )

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)},
        )

    assert response.status_code == 200

    async with _repository_connection() as connection:
        members = await UserRepository(connection).list_tenant_members(tenant_id)

    assert [member.id for member in members] == [member_id]


async def test_superadmin_can_manage_email_templates(db_connection: psycopg.Connection) -> None:
    suffix = uuid4().hex
    email = f"template-admin-{suffix}@example.com"
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status, is_superadmin)
            VALUES (%s, 'Template Admin', 'hash', 'active', true)
            RETURNING id
            """,
            (email,),
        )
        user_id = cursor.fetchone()[0]
        db_connection.commit()

    token = create_access_token(user_id=user_id, email=email, is_superadmin=True)
    slug = f"custom_template_{suffix}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        list_response = await client.get(
            "/api/v1/superadmin/email-templates",
            headers={"Authorization": f"Bearer {token}"},
        )
        upsert_response = await client.put(
            f"/api/v1/superadmin/email-templates/{slug}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "slug": slug,
                "name": "Custom Template",
                "description": "Template de teste",
                "subject_template": "Ola {{ user_name }}",
                "body_template": "<p>Mensagem para {{ user_name }}</p>",
                "variables_schema": {"required": ["user_name"]},
                "is_active": True,
            },
        )

    slugs = {item["slug"] for item in api_data(list_response)}
    assert list_response.status_code == 200
    assert {"account_activation", "tenant_invitation", "password_reset"}.issubset(slugs)
    assert upsert_response.status_code == 200
    assert api_data(upsert_response)["slug"] == slug

@asynccontextmanager
async def _repository_connection():
    async with engine.begin() as connection:
        yield connection
