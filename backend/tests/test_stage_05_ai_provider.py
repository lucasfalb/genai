import base64
import os

import psycopg
import pytest

import app.config as config_module
from engine.ai_provider import (
    AIProviderNotConfigured,
    AIProviderResolver,
    decrypt_api_key,
    encrypt_api_key,
)


TEST_FERNET_KEY = base64.urlsafe_b64encode(os.urandom(32)).decode()


@pytest.fixture(autouse=True)
def patch_encryption_key(monkeypatch):
    monkeypatch.setattr(config_module.settings, "ai_config_encryption_key", TEST_FERNET_KEY)
    monkeypatch.setattr(config_module.settings, "openai_api_key", None)


def test_encrypt_decrypt_round_trip():
    original = "sk-test-1234567890"
    encrypted = encrypt_api_key(original)
    assert encrypted != original
    assert decrypt_api_key(encrypted) == original


def test_encrypt_produces_different_ciphertext_each_call():
    key = "sk-same-key"
    c1 = encrypt_api_key(key)
    c2 = encrypt_api_key(key)
    assert c1 != c2


def test_encrypt_raises_without_config(monkeypatch):
    monkeypatch.setattr(config_module.settings, "ai_config_encryption_key", "")
    with pytest.raises(RuntimeError, match="not configured"):
        encrypt_api_key("sk-test")


async def test_resolver_falls_back_to_openai_api_key(monkeypatch, db_connection: psycopg.Connection):
    from database.connection import TenantContext, tenant_connection

    monkeypatch.setattr(config_module.settings, "openai_api_key", "sk-dev-fallback")
    tenant_id = _seed_tenant(db_connection)

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as connection:
        resolved = await AIProviderResolver(connection).resolve(tenant_id=tenant_id)

    assert resolved.api_key == "sk-dev-fallback"
    assert resolved.provider == "openai"


async def test_resolver_raises_when_nothing_configured(db_connection: psycopg.Connection):
    from database.connection import TenantContext, tenant_connection

    tenant_id = _seed_tenant(db_connection)

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as connection:
        with pytest.raises(AIProviderNotConfigured):
            await AIProviderResolver(connection).resolve(tenant_id=tenant_id)


async def test_resolver_uses_system_settings_config(db_connection: psycopg.Connection):
    from database.connection import TenantContext, tenant_connection

    tenant_id = _seed_tenant(db_connection)
    _seed_system_settings_config(db_connection, api_key_encrypted=encrypt_api_key("sk-platform-key"))

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as connection:
        resolved = await AIProviderResolver(connection).resolve(tenant_id=tenant_id)

    assert resolved.api_key == "sk-platform-key"
    assert resolved.provider == "openai"


async def test_resolver_tenant_overrides_system_settings(db_connection: psycopg.Connection):
    from database.connection import TenantContext, tenant_connection

    tenant_id = _seed_tenant(db_connection)
    _seed_system_settings_config(db_connection, api_key_encrypted=encrypt_api_key("sk-platform"))
    _seed_tenant_config(db_connection, tenant_id=tenant_id, api_key_encrypted=encrypt_api_key("sk-tenant"))

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as connection:
        resolved = await AIProviderResolver(connection).resolve(tenant_id=tenant_id)

    assert resolved.api_key == "sk-tenant"


def _seed_tenant(db_connection: psycopg.Connection):
    from uuid import uuid4

    with db_connection.cursor() as cursor:
        slug = f"ai-tenant-{uuid4().hex[:8]}"
        cursor.execute("INSERT INTO tenants (slug, name) VALUES (%s, 'AI Tenant') RETURNING id", (slug,))
        tenant_id = cursor.fetchone()[0]
        db_connection.commit()
    return tenant_id


def _seed_system_settings_config(db_connection: psycopg.Connection, *, api_key_encrypted: str):
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO system_settings (id, ai_provider, ai_api_key_encrypted, ai_default_model)
            VALUES (1, 'openai', %s, 'gpt-4.1-mini')
            ON CONFLICT (id) DO UPDATE SET ai_api_key_encrypted = EXCLUDED.ai_api_key_encrypted
            """,
            (api_key_encrypted,),
        )
        db_connection.commit()


def _seed_tenant_config(db_connection: psycopg.Connection, *, tenant_id, api_key_encrypted: str):
    import json

    providers_config = {
        "providers": [
            {
                "name": "openai",
                "api_key_encrypted": api_key_encrypted,
                "api_key_hint": "****",
                "enabled": True,
                "configured_at": "2026-05-10T00:00:00Z",
                "configured_by": str(tenant_id),
            }
        ]
    }
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE tenants
            SET providers_config = %s::jsonb
            WHERE id = %s
            """,
            (json.dumps(providers_config), tenant_id),
        )
        db_connection.commit()
