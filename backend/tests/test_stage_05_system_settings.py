import base64
import os
from uuid import uuid4

import psycopg
import pytest
from httpx import ASGITransport, AsyncClient

import app.config as config_module
from app.main import app
from app.security import create_access_token
from conftest import api_data, api_error

TEST_FERNET_KEY = base64.urlsafe_b64encode(os.urandom(32)).decode()


@pytest.fixture(autouse=True)
def patch_encryption_key(monkeypatch):
    monkeypatch.setattr(config_module.settings, "ai_config_encryption_key", TEST_FERNET_KEY)


async def test_public_system_settings_returns_safe_payload(db_connection: psycopg.Connection) -> None:
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO system_settings (
              id, platform_name, platform_public_url, platform_logo_url, maintenance_mode,
              registration_enabled, public_settings, ai_api_key_encrypted, smtp_pass_encrypted
            )
            VALUES (1, 'ContentFlow', 'https://app.example.com', 'https://app.example.com/logo.svg', false, true, '{"theme": "light"}', 'secret', 'secret')
            ON CONFLICT (id) DO UPDATE SET
              platform_name = EXCLUDED.platform_name,
              platform_public_url = EXCLUDED.platform_public_url,
              platform_logo_url = EXCLUDED.platform_logo_url,
              public_settings = EXCLUDED.public_settings,
              ai_api_key_encrypted = EXCLUDED.ai_api_key_encrypted,
              smtp_pass_encrypted = EXCLUDED.smtp_pass_encrypted
            """
        )
        db_connection.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/system-settings/public")

    data = api_data(response)
    assert response.status_code == 200
    assert data["platform_name"] == "ContentFlow"
    assert data["platform_logo_url"] == "https://app.example.com/logo.svg"
    assert data["public_settings"] == {"theme": "light"}
    assert "api_key" not in str(data).lower()
    assert "smtp_pass" not in str(data).lower()


async def test_superadmin_updates_system_settings_and_audits(db_connection: psycopg.Connection) -> None:
    superadmin = _seed_superadmin(db_connection, uuid4().hex)
    token = create_access_token(user_id=superadmin["id"], email=superadmin["email"], is_superadmin=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            "/api/v1/superadmin/system-settings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "platform_name": "ContentFlow",
                "platform_public_url": "https://app.example.com",
                "platform_logo_url": "https://app.example.com/logo.svg",
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "smtp_secure": False,
                "smtp_user": "smtp-user",
                "smtp_pass": "smtp-pass",
                "smtp_from": "ContentFlow <app@example.com>",
                "ai_provider": "openai",
                "ai_api_key": "sk-test",
                "ai_default_model": "gpt-4.1-mini",
                "custom_settings": {"billing.plan_label": "Growth"},
                "public_settings": {"support_url": "https://support.example.com"},
            },
        )

    data = api_data(response)
    assert response.status_code == 200
    assert data["platform_name"] == "ContentFlow"
    assert data["has_ai_api_key"] is True
    assert data["has_smtp_pass"] is True
    assert "sk-test" not in str(response.json())
    assert "smtp-pass" not in str(response.json())

    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT count(*)
            FROM audit_logs
            WHERE tenant_id IS NULL
              AND user_id = %s
              AND actor_type = 'superadmin'
              AND resource = 'system_settings'
              AND action = 'system_settings.updated'
            """,
            (superadmin["id"],),
        )
        assert cursor.fetchone()[0] == 1


async def test_superadmin_rejects_sensitive_custom_setting_keys(db_connection: psycopg.Connection) -> None:
    superadmin = _seed_superadmin(db_connection, uuid4().hex)
    token = create_access_token(user_id=superadmin["id"], email=superadmin["email"], is_superadmin=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            "/api/v1/superadmin/system-settings",
            headers={"Authorization": f"Bearer {token}"},
            json={"custom_settings": {"marketing.api_key": "plain"}},
        )

    assert response.status_code == 400
    assert api_error(response)["code"] == "SENSITIVE_CUSTOM_SETTING_KEY_IS_NOT_ALLOWED_MARKETING_API_KEY"


async def test_tenant_ai_settings_write_tenant_versions(db_connection: psycopg.Connection) -> None:
    setup = _seed_tenant_admin(db_connection, uuid4().hex)
    token = create_access_token(user_id=setup["user_id"], email=setup["email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            "/api/v1/tenant/settings/ai",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"provider": "openai", "api_key": "sk-tenant", "default_model": "gpt-4.1-mini"},
        )

    data = api_data(response)
    assert response.status_code == 200
    assert data["tenant_id"] == str(setup["tenant_id"])
    assert data["has_api_key"] is True
    assert "sk-tenant" not in str(response.json())

    with db_connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(setup["tenant_id"]),))
        cursor.execute(
            """
            SELECT count(*)
            FROM resource_versions
            WHERE tenant_id = %s
              AND changed_by = %s
              AND resource = 'tenant_ai_settings'
            """,
            (setup["tenant_id"], setup["user_id"]),
        )
        assert cursor.fetchone()[0] == 1
        cursor.execute("RESET app.current_tenant_id")


def _seed_superadmin(db_connection: psycopg.Connection, suffix: str) -> dict:
    email = f"settings-admin-{suffix}@example.com"
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status, is_superadmin)
            VALUES (%s, 'Admin', 'hash', 'active', true)
            RETURNING id
            """,
            (email,),
        )
        user_id = cursor.fetchone()[0]
        db_connection.commit()
    return {"id": user_id, "email": email}


def _seed_tenant_admin(db_connection: psycopg.Connection, suffix: str) -> dict:
    email = f"tenant-settings-admin-{suffix}@example.com"
    with db_connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tenants (slug, name) VALUES (%s, 'Settings Tenant') RETURNING id",
            (f"settings-tenant-{suffix}",),
        )
        tenant_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status)
            VALUES (%s, 'Tenant Admin', 'hash', 'active')
            RETURNING id
            """,
            (email,),
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
    return {"tenant_id": tenant_id, "user_id": user_id, "email": email}
