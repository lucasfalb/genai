from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.rbac import Role
from database.connection import TenantContext
from database.repositories.audit import AuditLogRepository
from database.repositories.versions import ResourceVersionRepository


def derive_actor(context: TenantContext) -> tuple[str, str]:
    if context.role == Role.SUPERADMIN.value:
        return "superadmin", "superadmin"
    return "user", context.role


async def record_tenant_mutation(
    *,
    connection: AsyncConnection,
    context: TenantContext,
    action: str,
    resource: str,
    resource_id: str,
    snapshot: dict | None = None,
    metadata: dict | None = None,
) -> None:
    await connection.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        {"tid": str(context.tenant_id)},
    )
    actor_type, actor_role = derive_actor(context)
    await AuditLogRepository(connection).record(
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        actor_type=actor_type,
        actor_role=actor_role,
        action=action,
        resource=resource,
        resource_id=resource_id,
        metadata=metadata or {},
    )
    if snapshot is not None:
        await ResourceVersionRepository(connection).record(
            tenant_id=context.tenant_id,
            changed_by=context.user_id,
            actor_type=actor_type,
            actor_role=actor_role,
            action=action,
            resource=resource,
            resource_id=resource_id,
            snapshot=snapshot,
            metadata=metadata or {},
        )
