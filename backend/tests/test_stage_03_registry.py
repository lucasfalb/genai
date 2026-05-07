from uuid import uuid4

import psycopg
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

import app.registry_cache as registry_cache_module
from app.main import app
from app.registry_cache import ToolMetadataCache
from app.security import create_access_token
from conftest import api_data
from database.connection import TenantContext, tenant_connection
from database.repositories.registry import RegistryRepository


async def test_superadmin_manages_global_skill_and_tool_catalog(db_connection: psycopg.Connection) -> None:
    suffix = uuid4().hex
    email = f"registry-admin-{suffix}@example.com"
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status, is_superadmin)
            VALUES (%s, 'Registry Admin', 'hash', 'active', true)
            RETURNING id
            """,
            (email,),
        )
        user_id = cursor.fetchone()[0]
        db_connection.commit()

    token = create_access_token(user_id=user_id, email=email, is_superadmin=True)
    skill_slug = f"crm_lookup_{suffix}"
    tool_slug = f"calculator_{suffix}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        skill_response = await client.put(
            f"/api/v1/superadmin/registry/skills/{skill_slug}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "slug": skill_slug,
                "name": "CRM Lookup",
                "description": "Lookup CRM records",
                "category": "crm",
                "prompt_block": "Use CRM lookup only for authorized tenant data.",
                "tool_schema": {"type": "function"},
                "executor": "skills.crm.lookup",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "requires_credential": True,
                "credential_schema": {"required": ["secret_ref"]},
                "is_active": True,
            },
        )
        tool_response = await client.put(
            f"/api/v1/superadmin/registry/tools/{tool_slug}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "slug": tool_slug,
                "name": "Calculator",
                "description": "Deterministic arithmetic helper",
                "category": "utility",
                "prompt_block": "Use for deterministic arithmetic.",
                "schema": {"type": "object"},
                "executor": "tools.builtin.calculator",
                "is_builtin": True,
            },
        )
        list_response = await client.get(
            "/api/v1/superadmin/registry/skills",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert skill_response.status_code == 200
    assert api_data(skill_response)["slug"] == skill_slug
    assert tool_response.status_code == 200
    assert api_data(tool_response)["schema"] == {"type": "object"}
    assert skill_slug in {item["slug"] for item in api_data(list_response)}


async def test_tenant_admin_configures_registry_and_metadata_without_secrets(
    db_connection: psycopg.Connection,
) -> None:
    suffix = uuid4().hex
    setup = _seed_registry_tenant(db_connection, suffix, role="tenant_admin")
    token = create_access_token(user_id=setup["user_id"], email=setup["email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        skill_response = await client.put(
            f"/api/v1/registry/instances/{setup['instance_id']}/skills/{setup['skill_slug']}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"is_enabled": True, "config": {"mode": "readonly"}},
        )
        tool_response = await client.put(
            f"/api/v1/registry/instances/{setup['instance_id']}/tools/{setup['tool_slug']}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"is_enabled": True, "config": {"precision": 2}},
        )
        credential_response = await client.put(
            f"/api/v1/registry/credentials/{setup['skill_slug']}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"secret_ref": "vault://tenant/crm", "metadata": {"provider": "hubspot"}},
        )
        metadata_response = await client.get(
            f"/api/v1/registry/instances/{setup['instance_id']}/metadata",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    assert skill_response.status_code == 200
    assert tool_response.status_code == 200
    assert credential_response.status_code == 200
    assert api_data(credential_response)["secret_ref"] == "vault://tenant/crm"
    metadata = api_data(metadata_response)
    assert metadata["skills"][0]["slug"] == setup["skill_slug"]
    assert metadata["tools"][0]["slug"] == setup["tool_slug"]
    assert "secret_ref" not in str(metadata)


async def test_registry_rejects_viewer_and_plain_secret_metadata(db_connection: psycopg.Connection) -> None:
    suffix = uuid4().hex
    viewer_setup = _seed_registry_tenant(db_connection, f"{suffix}viewer", role="viewer")
    viewer_token = create_access_token(user_id=viewer_setup["user_id"], email=viewer_setup["email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        forbidden_response = await client.put(
            f"/api/v1/registry/instances/{viewer_setup['instance_id']}/skills/{viewer_setup['skill_slug']}",
            headers={"Authorization": f"Bearer {viewer_token}", "X-Tenant-ID": str(viewer_setup["tenant_id"])},
            json={"is_enabled": True, "config": {}},
        )

    assert forbidden_response.status_code == 403

    admin_setup = _seed_registry_tenant(db_connection, f"{suffix}admin", role="tenant_admin")
    admin_token = create_access_token(user_id=admin_setup["user_id"], email=admin_setup["email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        secret_response = await client.put(
            f"/api/v1/registry/credentials/{admin_setup['skill_slug']}",
            headers={"Authorization": f"Bearer {admin_token}", "X-Tenant-ID": str(admin_setup["tenant_id"])},
            json={"secret_ref": "vault://tenant/crm", "metadata": {"api_key": "plain-secret"}},
        )

    assert secret_response.status_code == 400


async def test_tenant_admin_cannot_configure_instance_from_another_tenant(
    db_connection: psycopg.Connection,
) -> None:
    suffix = uuid4().hex
    tenant_a = _seed_registry_tenant(db_connection, f"{suffix}a", role="tenant_admin")
    tenant_b = _seed_registry_tenant(db_connection, f"{suffix}b", role="tenant_admin")
    token = create_access_token(user_id=tenant_a["user_id"], email=tenant_a["email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            f"/api/v1/registry/instances/{tenant_b['instance_id']}/skills/{tenant_a['skill_slug']}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_a["tenant_id"])},
            json={"is_enabled": True, "config": {}},
        )

    assert response.status_code == 404


async def test_tool_metadata_cache_hits_and_invalidates(db_connection: psycopg.Connection, monkeypatch) -> None:
    suffix = uuid4().hex
    setup = _seed_registry_tenant(db_connection, suffix, role="tenant_admin")
    fake_redis = _FakeRedis()
    monkeypatch.setattr(registry_cache_module, "redis_client", fake_redis)

    async with tenant_connection(
        TenantContext(tenant_id=setup["tenant_id"], user_id=setup["user_id"], role="tenant_admin")
    ) as connection:
        repository = RegistryRepository(connection)
        await repository.activate_skill(
            tenant_id=setup["tenant_id"],
            instance_id=setup["instance_id"],
            skill_slug=setup["skill_slug"],
            is_enabled=True,
            config={"mode": "cached"},
        )

        cache = ToolMetadataCache(connection)
        first = await cache.get(tenant_id=setup["tenant_id"], instance_id=setup["instance_id"])
        await connection.execute(
            text(
                """
                UPDATE agent_instance_skills
                SET config = '{"mode": "db-updated"}'
                WHERE tenant_id = :tenant_id AND instance_id = :instance_id
                """
            ),
            {"tenant_id": setup["tenant_id"], "instance_id": setup["instance_id"]},
        )
        second = await cache.get(tenant_id=setup["tenant_id"], instance_id=setup["instance_id"])
        await cache.invalidate(tenant_id=setup["tenant_id"], instance_id=setup["instance_id"])
        third = await cache.get(tenant_id=setup["tenant_id"], instance_id=setup["instance_id"])

    assert first.skills[0].config == {"mode": "cached"}
    assert second.skills[0].config == {"mode": "cached"}
    assert third.skills[0].config == {"mode": "db-updated"}
    assert fake_redis.get_calls == 3
    assert fake_redis.setex_calls == 2
    assert fake_redis.delete_calls == 1


def _seed_registry_tenant(db_connection: psycopg.Connection, suffix: str, *, role: str) -> dict:
    with db_connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tenants (slug, name) VALUES (%s, 'Registry Tenant') RETURNING id",
            (f"registry-tenant-{suffix}",),
        )
        tenant_id = cursor.fetchone()[0]
        email = f"registry-user-{suffix}@example.com"
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status)
            VALUES (%s, 'Registry User', 'hash', 'active')
            RETURNING id
            """,
            (email,),
        )
        user_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO memberships (user_id, tenant_id, role, status)
            VALUES (%s, %s, %s, 'active')
            """,
            (user_id, tenant_id, role),
        )
        cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(tenant_id),))
        cursor.execute(
            """
            INSERT INTO agent_instances (tenant_id, name, core_prompt, created_by, status)
            VALUES (%s, 'Registry Agent', 'You are a registry test agent.', %s, 'active')
            RETURNING id
            """,
            (tenant_id, user_id),
        )
        instance_id = cursor.fetchone()[0]
        cursor.execute("RESET app.current_tenant_id")

        skill_slug = f"crm_lookup_{suffix}"
        tool_slug = f"calculator_{suffix}"
        cursor.execute(
            """
            INSERT INTO skill_definitions
              (slug, name, prompt_block, tool_schema, executor, input_schema,
               output_schema, requires_credential, credential_schema, is_active)
            VALUES (%s, 'CRM Lookup', 'Use CRM lookup.', '{}', 'skills.crm.lookup',
                    '{}', '{}', true, '{}', true)
            """,
            (skill_slug,),
        )
        cursor.execute(
            """
            INSERT INTO tool_definitions (slug, name, prompt_block, schema, executor, is_builtin)
            VALUES (%s, 'Calculator', 'Use calculator.', '{}', 'tools.calculator', true)
            """,
            (tool_slug,),
        )
        db_connection.commit()

    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "email": email,
        "instance_id": instance_id,
        "skill_slug": skill_slug,
        "tool_slug": tool_slug,
    }


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.get_calls = 0
        self.setex_calls = 0
        self.delete_calls = 0

    async def get(self, key: str) -> str | None:
        self.get_calls += 1
        return self.values.get(key)

    async def setex(self, key: str, _ttl: int, value: str) -> None:
        self.setex_calls += 1
        self.values[key] = value

    async def delete(self, key: str) -> None:
        self.delete_calls += 1
        self.values.pop(key, None)
