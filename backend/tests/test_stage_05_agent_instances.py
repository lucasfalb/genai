from uuid import uuid4

import psycopg
from httpx import ASGITransport, AsyncClient

import api.v1.tenant_agent_instances as instances_api
from app.main import app
from app.security import create_access_token
from conftest import api_data, api_error


async def test_tenant_admin_creates_lists_and_gets_instance(
    db_connection: psycopg.Connection,
) -> None:
    setup = _seed_instances_tenant(db_connection, uuid4().hex)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_response = await client.post(
            "/api/v1/tenant/instances",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={
                "name": "My Agent",
                "core_prompt": "You are a helpful assistant.",
                "model": "gpt-4o",
                "temperature": 0.7,
            },
        )
        list_response = await client.get(
            "/api/v1/tenant/instances",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )
        instance_id = api_data(create_response)["id"]
        get_response = await client.get(
            f"/api/v1/tenant/instances/{instance_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    assert create_response.status_code == 201
    created = api_data(create_response)
    assert created["name"] == "My Agent"
    assert created["status"] == "inactive"
    assert created["model"] == "gpt-4o"
    assert created["temperature"] == 0.7
    assert created["rag_scope"] == []

    assert list_response.status_code == 200
    listed_ids = {item["id"] for item in api_data(list_response)}
    assert instance_id in listed_ids
    assert setup["instance_id"] in listed_ids

    assert get_response.status_code == 200
    assert api_data(get_response)["id"] == instance_id

    with db_connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(setup["tenant_id"]),))
        cursor.execute(
            "SELECT count(*) FROM audit_logs WHERE tenant_id = %s AND resource = 'agent_instances'",
            (setup["tenant_id"],),
        )
        assert cursor.fetchone()[0] == 1
        cursor.execute("RESET app.current_tenant_id")


async def test_tenant_admin_updates_and_archives_instance(
    db_connection: psycopg.Connection,
    monkeypatch,
) -> None:
    setup = _seed_instances_tenant(db_connection, uuid4().hex)
    fake_cache = _FakeToolMetadataCache()
    fake_prompt_cache = _FakePromptCache()
    monkeypatch.setattr(instances_api, "ToolMetadataCache", lambda _: fake_cache)
    monkeypatch.setattr(instances_api, "PromptCache", lambda _: fake_prompt_cache)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])
    instance_id = setup["instance_id"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        update_response = await client.patch(
            f"/api/v1/tenant/instances/{instance_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"name": "Updated Name", "status": "active"},
        )
        archive_response = await client.delete(
            f"/api/v1/tenant/instances/{instance_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )
        get_response = await client.get(
            f"/api/v1/tenant/instances/{instance_id}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    assert update_response.status_code == 200
    updated = api_data(update_response)
    assert updated["name"] == "Updated Name"
    assert updated["status"] == "active"

    assert archive_response.status_code == 200

    assert get_response.status_code == 200
    assert api_data(get_response)["status"] == "archived"

    assert len(fake_cache.invalidated) == 2
    assert len(fake_prompt_cache.invalidated) == 2

    with db_connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(setup["tenant_id"]),))
        cursor.execute(
            "SELECT count(*) FROM audit_logs WHERE tenant_id = %s AND resource = 'agent_instances'",
            (setup["tenant_id"],),
        )
        assert cursor.fetchone()[0] == 2
        cursor.execute(
            "SELECT count(*) FROM resource_versions WHERE tenant_id = %s AND resource = 'agent_instances'",
            (setup["tenant_id"],),
        )
        assert cursor.fetchone()[0] == 2
        cursor.execute("RESET app.current_tenant_id")


async def test_tenant_admin_updates_prompt_config_with_audit_and_cache_invalidation(
    db_connection: psycopg.Connection,
    monkeypatch,
) -> None:
    setup = _seed_instances_tenant(db_connection, uuid4().hex)
    fake_cache = _FakeToolMetadataCache()
    fake_prompt_cache = _FakePromptCache()
    monkeypatch.setattr(instances_api, "ToolMetadataCache", lambda _: fake_cache)
    monkeypatch.setattr(instances_api, "PromptCache", lambda _: fake_prompt_cache)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    payload = {
        "instruction_blocks": [
            {
                "id": "support-tone",
                "topic": "support",
                "title": "Support tone",
                "content": "Use concise and practical answers.",
                "priority": 10,
                "is_enabled": True,
            }
        ],
        "guardrails": [
            {
                "id": "no-legal-advice",
                "category": "compliance",
                "rule": "Never provide legal advice.",
                "severity": "blocking",
                "is_enabled": True,
                "metadata": {"source": "tenant-policy"},
            }
        ],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        update_response = await client.put(
            f"/api/v1/tenant/instances/{setup['instance_id']}/prompt-config",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json=payload,
        )
        get_response = await client.get(
            f"/api/v1/tenant/instances/{setup['instance_id']}/prompt-config",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    assert update_response.status_code == 200
    data = api_data(update_response)
    assert data["instruction_blocks"][0]["id"] == "support-tone"
    assert data["guardrails"][0]["severity"] == "blocking"
    assert api_data(get_response) == data
    assert len(fake_cache.invalidated) == 1
    assert len(fake_prompt_cache.invalidated) == 1

    with db_connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(setup["tenant_id"]),))
        cursor.execute(
            """
            SELECT action
            FROM audit_logs
            WHERE tenant_id = %s AND resource = 'agent_instances'
            ORDER BY created_at DESC LIMIT 1
            """,
            (setup["tenant_id"],),
        )
        assert cursor.fetchone()[0] == "agent_instance.prompt_config.updated"
        cursor.execute("RESET app.current_tenant_id")


async def test_prompt_config_rejects_sensitive_content(db_connection: psycopg.Connection) -> None:
    setup = _seed_instances_tenant(db_connection, uuid4().hex)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            f"/api/v1/tenant/instances/{setup['instance_id']}/prompt-config",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={
                "instruction_blocks": [
                    {
                        "id": "bad",
                        "topic": "security",
                        "title": "Bad",
                        "content": "Use api_key abc in every request.",
                    }
                ],
                "guardrails": [],
            },
        )

    assert response.status_code == 422


async def test_patch_with_no_fields_returns_400(
    db_connection: psycopg.Connection,
) -> None:
    setup = _seed_instances_tenant(db_connection, uuid4().hex)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/tenant/instances/{setup['instance_id']}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={},
        )

    assert response.status_code == 400


async def test_cross_tenant_isolation(
    db_connection: psycopg.Connection,
) -> None:
    setup = _seed_instances_tenant(db_connection, uuid4().hex)
    other = _seed_instances_tenant(db_connection, uuid4().hex)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        get_response = await client.get(
            f"/api/v1/tenant/instances/{other['instance_id']}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )
        patch_response = await client.patch(
            f"/api/v1/tenant/instances/{other['instance_id']}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"name": "Hacked"},
        )
        delete_response = await client.delete(
            f"/api/v1/tenant/instances/{other['instance_id']}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    assert get_response.status_code == 404
    assert patch_response.status_code == 404
    assert delete_response.status_code == 404


async def test_viewer_cannot_manage_instances(
    db_connection: psycopg.Connection,
) -> None:
    setup = _seed_instances_tenant(db_connection, uuid4().hex)
    viewer_token = create_access_token(user_id=setup["viewer_id"], email=setup["viewer_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_response = await client.post(
            "/api/v1/tenant/instances",
            headers={"Authorization": f"Bearer {viewer_token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"name": "Unauthorized", "core_prompt": "test"},
        )
        list_response = await client.get(
            "/api/v1/tenant/instances",
            headers={"Authorization": f"Bearer {viewer_token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )

    assert create_response.status_code == 403
    assert list_response.status_code == 403


async def test_superadmin_manages_instances_with_actor_context(
    db_connection: psycopg.Connection,
    monkeypatch,
) -> None:
    setup = _seed_instances_tenant(db_connection, uuid4().hex)
    fake_cache = _FakeToolMetadataCache()
    fake_prompt_cache = _FakePromptCache()
    monkeypatch.setattr(instances_api, "ToolMetadataCache", lambda _: fake_cache)
    monkeypatch.setattr(instances_api, "PromptCache", lambda _: fake_prompt_cache)
    token = create_access_token(
        user_id=setup["superadmin_id"],
        email=setup["superadmin_email"],
        is_superadmin=True,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        list_response = await client.get(
            "/api/v1/tenant/instances",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
        )
        update_response = await client.patch(
            f"/api/v1/tenant/instances/{setup['instance_id']}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"status": "active"},
        )

    assert list_response.status_code == 200
    assert update_response.status_code == 200
    assert [(tenant_id, str(instance_id)) for tenant_id, instance_id in fake_prompt_cache.invalidated] == [
        (setup["tenant_id"], setup["instance_id"])
    ]

    with db_connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(setup["tenant_id"]),))
        cursor.execute(
            """
            SELECT actor_type, actor_role
            FROM audit_logs
            WHERE tenant_id = %s AND resource = 'agent_instances'
            ORDER BY created_at DESC LIMIT 1
            """,
            (setup["tenant_id"],),
        )
        assert cursor.fetchone() == ("superadmin", "superadmin")
        cursor.execute("RESET app.current_tenant_id")


def _seed_instances_tenant(db_connection: psycopg.Connection, suffix: str) -> dict:
    with db_connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tenants (slug, name) VALUES (%s, 'Instances Tenant') RETURNING id",
            (f"instances-{suffix}",),
        )
        tenant_id = cursor.fetchone()[0]

        users = {}
        for key, role in (("admin", "tenant_admin"), ("viewer", "viewer")):
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
                "INSERT INTO memberships (user_id, tenant_id, role, status) VALUES (%s, %s, %s, 'active')",
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

        cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(tenant_id),))
        cursor.execute(
            """
            INSERT INTO agent_instances (tenant_id, name, core_prompt, created_by, status)
            VALUES (%s, 'Test Instance', 'You are helpful.', %s, 'inactive')
            RETURNING id
            """,
            (tenant_id, users["admin"]["id"]),
        )
        instance_id = cursor.fetchone()[0]
        cursor.execute("RESET app.current_tenant_id")

        db_connection.commit()

    return {
        "tenant_id": tenant_id,
        "admin_id": users["admin"]["id"],
        "admin_email": users["admin"]["email"],
        "viewer_id": users["viewer"]["id"],
        "viewer_email": users["viewer"]["email"],
        "superadmin_id": superadmin_id,
        "superadmin_email": superadmin_email,
        "instance_id": str(instance_id),
    }


class _FakeToolMetadataCache:
    def __init__(self) -> None:
        self.invalidated: list[tuple] = []

    async def invalidate(self, *, tenant_id, instance_id) -> None:
        self.invalidated.append((tenant_id, instance_id))


class _FakePromptCache:
    def __init__(self) -> None:
        self.invalidated: list[tuple] = []

    async def invalidate(self, *, tenant_id, instance_id) -> None:
        self.invalidated.append((tenant_id, instance_id))
