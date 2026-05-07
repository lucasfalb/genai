import base64
import os

import psycopg
import pytest
from cryptography.fernet import Fernet

import app.config as config_module
from engine.ai_provider import (
    AIProviderNotConfigured,
    AIProviderResolver,
    decrypt_api_key,
    encrypt_api_key,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_FERNET_KEY = base64.urlsafe_b64encode(os.urandom(32)).decode()


@pytest.fixture(autouse=True)
def patch_encryption_key(monkeypatch):
    monkeypatch.setattr(config_module.settings, "ai_config_encryption_key", TEST_FERNET_KEY)
    monkeypatch.setattr(config_module.settings, "openai_api_key", None)


# ---------------------------------------------------------------------------
# Encryption round-trip
# ---------------------------------------------------------------------------

def test_encrypt_decrypt_round_trip():
    original = "sk-test-1234567890"
    encrypted = encrypt_api_key(original)
    assert encrypted != original
    assert decrypt_api_key(encrypted) == original


def test_encrypt_produces_different_ciphertext_each_call():
    key = "sk-same-key"
    c1 = encrypt_api_key(key)
    c2 = encrypt_api_key(key)
    assert c1 != c2  # Fernet uses random IV


def test_encrypt_raises_without_config(monkeypatch):
    monkeypatch.setattr(config_module.settings, "ai_config_encryption_key", "")
    with pytest.raises(RuntimeError, match="not configured"):
        encrypt_api_key("sk-test")


# ---------------------------------------------------------------------------
# Resolver — dev fallback
# ---------------------------------------------------------------------------

async def test_resolver_falls_back_to_openai_api_key(monkeypatch, db_connection: psycopg.Connection):
    monkeypatch.setattr(config_module.settings, "openai_api_key", "sk-dev-fallback")

    from database.connection import TenantContext, tenant_connection
    from uuid import uuid4

    tenant_id = _seed_tenant(db_connection)

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as connection:
        resolved = await AIProviderResolver(connection).resolve(tenant_id=tenant_id)

    assert resolved.api_key == "sk-dev-fallback"
    assert resolved.provider == "openai"


async def test_resolver_raises_when_nothing_configured(db_connection: psycopg.Connection):
    from database.connection import TenantContext, tenant_connection
    from uuid import uuid4

    tenant_id = _seed_tenant(db_connection)

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as connection:
        with pytest.raises(AIProviderNotConfigured):
            await AIProviderResolver(connection).resolve(tenant_id=tenant_id)


# ---------------------------------------------------------------------------
# Resolver — platform config
# ---------------------------------------------------------------------------

async def test_resolver_uses_platform_config(db_connection: psycopg.Connection):
    from database.connection import TenantContext, tenant_connection

    tenant_id = _seed_tenant(db_connection)
    encrypted = encrypt_api_key("sk-platform-key")
    _seed_platform_config(db_connection, api_key_encrypted=encrypted)

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as connection:
        resolved = await AIProviderResolver(connection).resolve(tenant_id=tenant_id)

    assert resolved.api_key == "sk-platform-key"
    assert resolved.provider == "openai"


# ---------------------------------------------------------------------------
# Resolver — tenant config overrides platform
# ---------------------------------------------------------------------------

async def test_resolver_tenant_overrides_platform(db_connection: psycopg.Connection):
    from database.connection import TenantContext, tenant_connection

    tenant_id = _seed_tenant(db_connection)
    _seed_platform_config(db_connection, api_key_encrypted=encrypt_api_key("sk-platform"))
    _seed_tenant_config(db_connection, tenant_id=tenant_id, api_key_encrypted=encrypt_api_key("sk-tenant"))

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as connection:
        resolved = await AIProviderResolver(connection).resolve(tenant_id=tenant_id)

    assert resolved.api_key == "sk-tenant"


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def _seed_tenant(db_connection: psycopg.Connection):
    from uuid import uuid4
    with db_connection.cursor() as cursor:
        slug = f"ai-tenant-{uuid4().hex[:8]}"
        cursor.execute("INSERT INTO tenants (slug, name) VALUES (%s, 'AI Tenant') RETURNING id", (slug,))
        tenant_id = cursor.fetchone()[0]
        db_connection.commit()
    return tenant_id


def _seed_platform_config(db_connection: psycopg.Connection, *, api_key_encrypted: str):
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO platform_ai_configs (provider, api_key_encrypted, default_model)
            VALUES ('openai', %s, 'gpt-4.1-mini')
            """,
            (api_key_encrypted,),
        )
        db_connection.commit()


def _seed_tenant_config(db_connection: psycopg.Connection, *, tenant_id, api_key_encrypted: str):
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO tenant_ai_configs (tenant_id, provider, api_key_encrypted)
            VALUES (%s, 'openai', %s)
            """,
            (tenant_id, api_key_encrypted),
        )
        db_connection.commit()
