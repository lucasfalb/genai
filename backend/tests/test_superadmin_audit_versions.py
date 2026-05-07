from uuid import uuid4

from sqlalchemy import text

from database.connection import TenantContext, engine, tenant_connection
from database.repositories.audit import AuditLogRepository
from database.repositories.users import UserRepository
from database.repositories.versions import ResourceVersionRepository


async def test_superadmin_tenant_action_is_audited_and_versioned_but_not_listed_as_member() -> None:
    suffix = uuid4().hex
    async with engine.begin() as connection:
        tenant = (
            await connection.execute(
                text("INSERT INTO tenants (slug, name) VALUES (:slug, 'Audited Tenant') RETURNING id"),
                {"slug": f"audited-tenant-{suffix}"},
            )
        ).one()
        superadmin = (
            await connection.execute(
                text(
                    """
                    INSERT INTO users (email, name, password_hash, status, is_superadmin)
                    VALUES (:email, 'Platform Admin', 'hash', 'active', true)
                    RETURNING id
                    """
                ),
                {"email": f"audited-superadmin-{suffix}@example.com"},
            )
        ).one()
        member = (
            await connection.execute(
                text(
                    """
                    INSERT INTO users (email, name, password_hash, status)
                    VALUES (:email, 'Tenant Member', 'hash', 'active')
                    RETURNING id
                    """
                ),
                {"email": f"audited-member-{suffix}@example.com"},
            )
        ).one()
        await connection.execute(
            text(
                """
                INSERT INTO memberships (user_id, tenant_id, role, status)
                VALUES (:user_id, :tenant_id, 'member', 'active')
                """
            ),
            {"user_id": member.id, "tenant_id": tenant.id},
        )

    async with tenant_connection(TenantContext(tenant_id=tenant.id, user_id=superadmin.id, role="superadmin")) as connection:
        audit = await AuditLogRepository(connection).record(
            tenant_id=tenant.id,
            user_id=superadmin.id,
            actor_type="superadmin",
            actor_role="superadmin",
            action="tenant.settings.updated",
            resource="tenants",
            resource_id=str(tenant.id),
            metadata={"field": "settings"},
        )
        version = await ResourceVersionRepository(connection).record(
            tenant_id=tenant.id,
            changed_by=superadmin.id,
            actor_type="superadmin",
            actor_role="superadmin",
            action="tenant.settings.updated",
            resource="tenants",
            resource_id=str(tenant.id),
            snapshot={"settings": {"support_email": "support@example.com"}},
        )
        members = await UserRepository(connection).list_tenant_members(tenant.id)

    assert audit.tenant_id == tenant.id
    assert audit.user_id == superadmin.id
    assert audit.actor_type == "superadmin"
    assert version.tenant_id == tenant.id
    assert version.changed_by == superadmin.id
    assert version.actor_type == "superadmin"
    assert [item.id for item in members] == [member.id]
