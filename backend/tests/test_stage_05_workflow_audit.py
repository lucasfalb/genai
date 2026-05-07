from uuid import uuid4

import psycopg
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

import api.v1.tenant_agent_instances as instances_api
import api.v1.tenant_members as members_api
from app.main import app
from app.security import create_access_token
from app.workflow_audit import derive_actor, record_tenant_mutation
from conftest import api_data
from database.connection import TenantContext, engine
from database.repositories.audit import AuditLogRepository


async def test_derive_actor_returns_user_for_tenant_role() -> None:
    context = TenantContext(tenant_id=uuid4(), user_id=uuid4(), role="tenant_admin")
    assert derive_actor(context) == ("user", "tenant_admin")

    context_viewer = TenantContext(tenant_id=uuid4(), user_id=uuid4(), role="viewer")
    assert derive_actor(context_viewer) == ("user", "viewer")


async def test_derive_actor_returns_superadmin_for_superadmin_role() -> None:
    context = TenantContext(tenant_id=uuid4(), user_id=uuid4(), role="superadmin")
    assert derive_actor(context) == ("superadmin", "superadmin")


async def test_record_tenant_mutation_writes_audit_and_version() -> None:
    suffix = uuid4().hex
    async with engine.begin() as connection:
        tenant = (
            await connection.execute(
                text("INSERT INTO tenants (slug, name) VALUES (:slug, 'Workflow Tenant') RETURNING id"),
                {"slug": f"wf-tenant-{suffix}"},
            )
        ).one()
        user = (
            await connection.execute(
                text(
                    "INSERT INTO users (email, status) VALUES (:email, 'active') RETURNING id"
                ),
                {"email": f"wf-user-{suffix}@example.com"},
            )
        ).one()

        context = TenantContext(tenant_id=tenant.id, user_id=user.id, role="tenant_admin")
        await record_tenant_mutation(
            connection=connection,
            context=context,
            action="test.created",
            resource="test_resource",
            resource_id="res-1",
            snapshot={"field": "value"},
            metadata={"info": "data"},
        )

        audit_count = await connection.scalar(
            text(
                "SELECT count(*) FROM audit_logs WHERE tenant_id = :tid AND resource = 'test_resource'"
            ),
            {"tid": tenant.id},
        )
        version_count = await connection.scalar(
            text(
                "SELECT count(*) FROM resource_versions WHERE tenant_id = :tid AND resource = 'test_resource'"
            ),
            {"tid": tenant.id},
        )

    assert audit_count == 1
    assert version_count == 1


async def test_record_tenant_mutation_superadmin_actor_context() -> None:
    suffix = uuid4().hex
    async with engine.begin() as connection:
        tenant = (
            await connection.execute(
                text("INSERT INTO tenants (slug, name) VALUES (:slug, 'SA Workflow Tenant') RETURNING id"),
                {"slug": f"sa-wf-{suffix}"},
            )
        ).one()
        superadmin = (
            await connection.execute(
                text(
                    "INSERT INTO users (email, status, is_superadmin) VALUES (:email, 'active', true) RETURNING id"
                ),
                {"email": f"sa-wf-{suffix}@example.com"},
            )
        ).one()

        context = TenantContext(tenant_id=tenant.id, user_id=superadmin.id, role="superadmin")
        await record_tenant_mutation(
            connection=connection,
            context=context,
            action="resource.updated",
            resource="test_resource",
            resource_id="res-2",
            snapshot={"field": "value"},
            metadata={},
        )

        row = (
            await connection.execute(
                text(
                    "SELECT actor_type, actor_role FROM audit_logs WHERE tenant_id = :tid AND resource = 'test_resource'"
                ),
                {"tid": tenant.id},
            )
        ).one()

    assert row.actor_type == "superadmin"
    assert row.actor_role == "superadmin"


async def test_record_tenant_mutation_redacts_sensitive_metadata() -> None:
    suffix = uuid4().hex
    async with engine.begin() as connection:
        tenant = (
            await connection.execute(
                text("INSERT INTO tenants (slug, name) VALUES (:slug, 'Redact Tenant') RETURNING id"),
                {"slug": f"redact-{suffix}"},
            )
        ).one()
        user = (
            await connection.execute(
                text("INSERT INTO users (email, status) VALUES (:email, 'active') RETURNING id"),
                {"email": f"redact-{suffix}@example.com"},
            )
        ).one()

        context = TenantContext(tenant_id=tenant.id, user_id=user.id, role="tenant_admin")
        await record_tenant_mutation(
            connection=connection,
            context=context,
            action="credential.stored",
            resource="credentials",
            resource_id="cred-1",
            metadata={"name": "My Cred", "api_key": "plain-secret", "safe_field": "visible"},
        )

        metadata = await connection.scalar(
            text(
                "SELECT metadata FROM audit_logs WHERE tenant_id = :tid AND resource = 'credentials'"
            ),
            {"tid": tenant.id},
        )

    assert metadata["api_key"] == "[REDACTED]"
    assert metadata["name"] == "My Cred"
    assert metadata["safe_field"] == "visible"


async def test_membership_cache_invalidated_and_audit_recorded_on_update(
    db_connection: psycopg.Connection,
    monkeypatch,
) -> None:
    setup = _seed_audit_tenant(db_connection, uuid4().hex)
    fake_redis = _FakeRedis()
    monkeypatch.setattr(members_api, "redis_client", fake_redis)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/tenant/members/{setup['member_id']}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"role": "viewer"},
        )

    assert response.status_code == 200
    assert f"membership:{setup['member_id']}:{setup['tenant_id']}" in fake_redis.deleted

    with db_connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(setup["tenant_id"]),))
        cursor.execute(
            "SELECT actor_type, actor_role FROM audit_logs WHERE tenant_id = %s AND resource = 'memberships'",
            (setup["tenant_id"],),
        )
        row = cursor.fetchone()
        assert row == ("user", "tenant_admin")
        cursor.execute("RESET app.current_tenant_id")


async def test_instance_metadata_cache_invalidated_and_audit_recorded_on_update(
    db_connection: psycopg.Connection,
    monkeypatch,
) -> None:
    setup = _seed_audit_tenant(db_connection, uuid4().hex)
    fake_cache = _FakeToolMetadataCache()
    monkeypatch.setattr(instances_api, "ToolMetadataCache", lambda _: fake_cache)
    token = create_access_token(user_id=setup["admin_id"], email=setup["admin_email"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/tenant/instances/{setup['instance_id']}",
            headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": str(setup["tenant_id"])},
            json={"status": "active"},
        )

    assert response.status_code == 200
    assert len(fake_cache.invalidated) == 1

    with db_connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(setup["tenant_id"]),))
        cursor.execute(
            "SELECT actor_type, actor_role FROM audit_logs WHERE tenant_id = %s AND resource = 'agent_instances'",
            (setup["tenant_id"],),
        )
        row = cursor.fetchone()
        assert row == ("user", "tenant_admin")
        cursor.execute("RESET app.current_tenant_id")


def _seed_audit_tenant(db_connection: psycopg.Connection, suffix: str) -> dict:
    with db_connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tenants (slug, name) VALUES (%s, 'Audit WF Tenant') RETURNING id",
            (f"audit-wf-{suffix}",),
        )
        tenant_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status)
            VALUES (%s, 'Admin', 'hash', 'active')
            RETURNING id
            """,
            (f"admin-{suffix}@example.com",),
        )
        admin_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO memberships (user_id, tenant_id, role, status) VALUES (%s, %s, 'tenant_admin', 'active')",
            (admin_id, tenant_id),
        )

        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, status)
            VALUES (%s, 'Member', 'hash', 'active')
            RETURNING id
            """,
            (f"member-{suffix}@example.com",),
        )
        member_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO memberships (user_id, tenant_id, role, status) VALUES (%s, %s, 'member', 'active')",
            (member_id, tenant_id),
        )

        cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", (str(tenant_id),))
        cursor.execute(
            """
            INSERT INTO agent_instances (tenant_id, name, core_prompt, created_by, status)
            VALUES (%s, 'WF Instance', 'You are helpful.', %s, 'inactive')
            RETURNING id
            """,
            (tenant_id, admin_id),
        )
        instance_id = cursor.fetchone()[0]
        cursor.execute("RESET app.current_tenant_id")

        db_connection.commit()

    return {
        "tenant_id": tenant_id,
        "admin_id": admin_id,
        "admin_email": f"admin-{suffix}@example.com",
        "member_id": member_id,
        "instance_id": str(instance_id),
    }


class _FakeRedis:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def delete(self, key: str) -> None:
        self.deleted.append(key)

    async def get(self, key: str) -> None:
        return None

    async def setex(self, key: str, ttl: int, value: str) -> None:
        pass


class _FakeToolMetadataCache:
    def __init__(self) -> None:
        self.invalidated: list[tuple] = []

    async def invalidate(self, *, tenant_id, instance_id) -> None:
        self.invalidated.append((tenant_id, instance_id))
