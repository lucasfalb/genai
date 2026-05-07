from uuid import uuid4

from sqlalchemy import text

from database.connection import engine
from database.repositories.audit import AuditLogRepository


async def test_audit_repository_redacts_sensitive_metadata() -> None:
    suffix = uuid4().hex
    async with engine.begin() as connection:
        tenant = (
            await connection.execute(
                text("INSERT INTO tenants (slug, name) VALUES (:slug, 'Audit Tenant') RETURNING id"),
                {"slug": f"audit-tenant-{suffix}"},
            )
        ).one()
        user = (
            await connection.execute(
                text(
                    """
                    INSERT INTO users (email, name, status)
                    VALUES (:email, 'Audit User', 'active')
                    RETURNING id
                    """
                ),
                {"email": f"audit-user-{suffix}@example.com"},
            )
        ).one()

        repository = AuditLogRepository(connection)
        record = await repository.record(
            tenant_id=tenant.id,
            user_id=user.id,
            action="credential.created",
            resource="tool_credentials",
            metadata={"api_key": "plain-secret", "nested": {"token": "plain-token"}, "safe": "value"},
        )

        metadata = await connection.scalar(
            text("SELECT metadata FROM audit_logs WHERE id = :id"),
            {"id": record.id},
        )

    assert metadata["api_key"] == "[REDACTED]"
    assert metadata["nested"]["token"] == "[REDACTED]"
    assert metadata["safe"] == "value"
    assert record.actor_type == "user"
