from uuid import uuid4

from sqlalchemy import text

from database.connection import TenantContext, tenant_connection
from database.connection import engine
from database.repositories.sessions import SessionRepository


async def test_session_repository_appends_messages_in_order() -> None:
    suffix = uuid4().hex
    async with engine.begin() as connection:
        tenant_row = (
            await connection.execute(
                text(
                    """
                    INSERT INTO tenants (slug, name)
                    VALUES (:slug, 'Repository Tenant')
                    RETURNING id
                    """
                ),
                {"slug": f"repo-tenant-{suffix}"},
            )
        ).one()
        user_row = (
            await connection.execute(
                text(
                    """
                    INSERT INTO users (email, name, status)
                    VALUES (:email, 'Repo Admin', 'active')
                    RETURNING id
                    """
                ),
                {"email": f"repo-admin-{suffix}@example.com"},
            )
        ).one()
        tenant_id = tenant_row.id
        user_id = user_row.id

    async with tenant_connection(TenantContext(tenant_id=tenant_id)) as connection:
        instance_row = (
            await connection.execute(
                text(
                    """
                    INSERT INTO agent_instances (tenant_id, name, core_prompt, created_by, status)
                    VALUES (:tenant_id, 'Repository Support', 'You are support.', :user_id, 'active')
                    RETURNING id
                    """
                ),
                {"tenant_id": tenant_id, "user_id": user_id},
            )
        ).one()
        instance_id = instance_row.id

        repository = SessionRepository(connection)
        session = await repository.create_session(
            tenant_id=tenant_id,
            instance_id=instance_id,
            channel="api",
            user_ref="user-1",
        )

        first = await repository.append_message(
            tenant_id=tenant_id,
            session_id=session.id,
            role="user",
            content="hello",
        )
        second = await repository.append_message(
            tenant_id=tenant_id,
            session_id=session.id,
            role="assistant",
            content="hi",
        )

        last_message_at = await connection.scalar(
            text("SELECT last_message_at FROM sessions WHERE id = :session_id"),
            {"session_id": session.id},
        )

    assert first.sequence_no == 1
    assert second.sequence_no == 2
    assert last_message_at is not None
