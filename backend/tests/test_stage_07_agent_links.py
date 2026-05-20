from uuid import UUID, uuid4

import psycopg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

import api.v1.tenant_agent_links as links_api
from app.main import app
from app.security import create_access_token
from conftest import api_data
from database.connection import TenantContext, tenant_connection
from database.repositories.agent_links import AgentLinkRepository


async def test_agent_link_repository_create_list_get_update_delete(db_connection: psycopg.Connection) -> None:
    setup = _seed_handoff_tenant(db_connection, uuid4().hex)

    async with tenant_connection(TenantContext(tenant_id=UUID(setup["tenant_id"]))) as connection:
        repo = AgentLinkRepository(connection)
        link = await repo.create(
            tenant_id=UUID(setup["tenant_id"]),
            source_instance_id=UUID(setup["source_id"]),
            target_instance_id=UUID(setup["target_id"]),
            transfer_tool_name="transfer_to_billing",
            trigger_description="Use when billing help is needed.",
            handoff_instructions=None,
            context_policy={"max_messages": 8},
            transfer_mode="llm_decision",
        )
        listed = await repo.list_by_source(
            tenant_id=UUID(setup["tenant_id"]),
            source_instance_id=UUID(setup["source_id"]),
        )
        found = await repo.get(
            tenant_id=UUID(setup["tenant_id"]),
            source_instance_id=UUID(setup["source_id"]),
            link_id=link.id,
        )
        updated = await repo.update(
            tenant_id=UUID(setup["tenant_id"]),
            source_instance_id=UUID(setup["source_id"]),
            link_id=link.id,
            trigger_description="Use when invoices or payments are mentioned.",
            transfer_mode="router_classifier",
            is_enabled=False,
        )
        disabled = await repo.set_enabled(
            tenant_id=UUID(setup["tenant_id"]),
            source_instance_id=UUID(setup["source_id"]),
            link_id=link.id,
            is_enabled=True,
        )
        deleted = await repo.delete(
            tenant_id=UUID(setup["tenant_id"]),
            source_instance_id=UUID(setup["source_id"]),
            link_id=link.id,
        )

    assert link.transfer_mode == "llm_decision"
    assert [item.id for item in listed] == [link.id]
    assert found == link
    assert updated is not None
    assert updated.trigger_description == "Use when invoices or payments are mentioned."
    assert updated.transfer_mode == "router_classifier"
    assert updated.is_enabled is False
    assert disabled is not None
    assert disabled.is_enabled is True
    assert deleted == disabled


async def test_agent_link_repository_enforces_unique_source_target(db_connection: psycopg.Connection) -> None:
    setup = _seed_handoff_tenant(db_connection, uuid4().hex)

    with pytest.raises(IntegrityError):
        async with tenant_connection(TenantContext(tenant_id=UUID(setup["tenant_id"]))) as connection:
            repo = AgentLinkRepository(connection)
            kwargs = {
                "tenant_id": UUID(setup["tenant_id"]),
                "source_instance_id": UUID(setup["source_id"]),
                "target_instance_id": UUID(setup["target_id"]),
                "transfer_tool_name": "transfer_to_billing",
                "trigger_description": "Use when billing help is needed.",
                "handoff_instructions": None,
                "context_policy": {"max_messages": 8},
                "transfer_mode": "llm_decision",
            }
            await repo.create(**kwargs)
            await repo.create(**{**kwargs, "transfer_tool_name": "transfer_to_billing_again"})


async def test_agent_link_repository_lists_only_requested_source(db_connection: psycopg.Connection) -> None:
    setup = _seed_handoff_tenant(db_connection, uuid4().hex)

    async with tenant_connection(TenantContext(tenant_id=UUID(setup["tenant_id"]))) as connection:
        repo = AgentLinkRepository(connection)
        source_link = await repo.create(
            tenant_id=UUID(setup["tenant_id"]),
            source_instance_id=UUID(setup["source_id"]),
            target_instance_id=UUID(setup["target_id"]),
            transfer_tool_name="transfer_to_billing",
            trigger_description="Use when billing help is needed.",
            handoff_instructions=None,
            context_policy={"max_messages": 8},
            transfer_mode="llm_decision",
        )
        await repo.create(
            tenant_id=UUID(setup["tenant_id"]),
            source_instance_id=UUID(setup["other_source_id"]),
            target_instance_id=UUID(setup["target_id"]),
            transfer_tool_name="transfer_from_other",
            trigger_description="Use from another source.",
            handoff_instructions=None,
            context_policy={"max_messages": 8},
            transfer_mode="llm_decision",
        )
        listed = await repo.list_by_source(
            tenant_id=UUID(setup["tenant_id"]),
            source_instance_id=UUID(setup["source_id"]),
        )

    assert [item.id for item in listed] == [source_link.id]


async def test_tenant_admin_creates_lists_updates_and_deletes_agent_link(
    db_connection: psycopg.Connection,
    monkeypatch,
) -> None:
    setup = _seed_handoff_tenant(db_connection, uuid4().hex)
    fake_cache = _FakeToolMetadataCache()
    fake_prompt_cache = _FakePromptCache()
    monkeypatch.setattr(links_api, "ToolMetadataCache", lambda _: fake_cache)
    monkeypatch.setattr(links_api, "PromptCache", lambda _: fake_prompt_cache)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": setup["tenant_id"]}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_response = await client.post(
            f"/api/v1/tenant/instances/{setup['source_id']}/links",
            headers=headers,
            json={
                "target_instance_id": setup["target_id"],
                "transfer_tool_name": "transfer_to_billing",
                "trigger_description": "Use when billing help is needed.",
            },
        )
        link_id = api_data(create_response)["id"]
        list_response = await client.get(
            f"/api/v1/tenant/instances/{setup['source_id']}/links",
            headers=headers,
        )
        update_response = await client.patch(
            f"/api/v1/tenant/instances/{setup['source_id']}/links/{link_id}",
            headers=headers,
            json={"transfer_mode": "router_classifier", "is_enabled": False},
        )
        delete_response = await client.delete(
            f"/api/v1/tenant/instances/{setup['source_id']}/links/{link_id}",
            headers=headers,
        )

    assert create_response.status_code == 201
    created = api_data(create_response)
    assert created["source_instance_id"] == setup["source_id"]
    assert created["target_instance_id"] == setup["target_id"]
    assert created["transfer_mode"] == "llm_decision"
    assert api_data(list_response)[0]["id"] == link_id
    assert api_data(update_response)["transfer_mode"] == "router_classifier"
    assert api_data(update_response)["is_enabled"] is False
    assert delete_response.status_code == 200
    assert [(str(tenant_id), str(instance_id)) for tenant_id, instance_id in fake_cache.invalidated] == [
        (setup["tenant_id"], setup["source_id"]),
        (setup["tenant_id"], setup["source_id"]),
        (setup["tenant_id"], setup["source_id"]),
    ]
    assert len(fake_prompt_cache.invalidated) == 3


async def test_agent_link_api_rejects_self_link_duplicate_and_cross_tenant_target(
    db_connection: psycopg.Connection,
) -> None:
    setup = _seed_handoff_tenant(db_connection, uuid4().hex)
    other = _seed_handoff_tenant(db_connection, uuid4().hex)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": setup["tenant_id"]}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        self_response = await client.post(
            f"/api/v1/tenant/instances/{setup['source_id']}/links",
            headers=headers,
            json={
                "target_instance_id": setup["source_id"],
                "transfer_tool_name": "transfer_to_self",
                "trigger_description": "Bad self transfer.",
            },
        )
        create_response = await client.post(
            f"/api/v1/tenant/instances/{setup['source_id']}/links",
            headers=headers,
            json={
                "target_instance_id": setup["target_id"],
                "transfer_tool_name": "transfer_to_billing",
                "trigger_description": "Use when billing help is needed.",
            },
        )
        duplicate_response = await client.post(
            f"/api/v1/tenant/instances/{setup['source_id']}/links",
            headers=headers,
            json={
                "target_instance_id": setup["target_id"],
                "transfer_tool_name": "transfer_to_billing_again",
                "trigger_description": "Duplicate.",
            },
        )
        cross_tenant_response = await client.post(
            f"/api/v1/tenant/instances/{setup['source_id']}/links",
            headers=headers,
            json={
                "target_instance_id": other["target_id"],
                "transfer_tool_name": "transfer_to_other_tenant",
                "trigger_description": "Bad tenant transfer.",
            },
        )

    assert self_response.status_code == 400
    assert create_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert cross_tenant_response.status_code == 404


def _seed_handoff_tenant(db_connection: psycopg.Connection, suffix: str) -> dict[str, str]:
    with db_connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tenants (slug, name) VALUES (%s, 'Handoff Tenant') RETURNING id",
            (f"handoff-{suffix}",),
        )
        tenant_id = cursor.fetchone()[0]

        admin_email = f"handoff-admin-{suffix}@example.com"
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status)
            VALUES (%s, 'Handoff Admin', 'hash', 'active')
            RETURNING id
            """,
            (admin_email,),
        )
        admin_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO memberships (user_id, tenant_id, role, status) VALUES (%s, %s, 'tenant_admin', 'active')",
            (admin_id, tenant_id),
        )

        cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(tenant_id),))
        instance_ids = []
        for name in ("Support", "Billing", "Escalations"):
            cursor.execute(
                """
                INSERT INTO agent_instances (tenant_id, name, core_prompt, created_by, status)
                VALUES (%s, %s, %s, %s, 'active')
                RETURNING id
                """,
                (tenant_id, name, f"You are {name}.", admin_id),
            )
            instance_ids.append(str(cursor.fetchone()[0]))
        cursor.execute("RESET app.current_tenant_id")
        db_connection.commit()

    return {
        "tenant_id": str(tenant_id),
        "admin_id": str(admin_id),
        "admin_email": admin_email,
        "source_id": instance_ids[0],
        "target_id": instance_ids[1],
        "other_source_id": instance_ids[2],
    }


class _FakeToolMetadataCache:
    def __init__(self) -> None:
        self.invalidated: list[tuple] = []

    async def get(self, *, tenant_id, instance_id):
        return _FakeToolMetadata()

    async def invalidate(self, *, tenant_id, instance_id) -> None:
        self.invalidated.append((tenant_id, instance_id))


class _FakePromptCache:
    def __init__(self) -> None:
        self.invalidated: list[tuple] = []

    async def invalidate(self, *, tenant_id, instance_id) -> None:
        self.invalidated.append((tenant_id, instance_id))


class _FakeToolMetadata:
    skills: list = []
    tools: list = []
