from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncConnection

from app.rbac import Permission
from app.responses import api_success
from app.schemas import ApiResponse, SuperadminAuditLogResponse
from database.connection import TenantContext
from database.repositories.audit import AuditLogRepository
from dependencies.auth import get_connection, require_permission

router = APIRouter(prefix="/tenant/audit", tags=["tenant-audit"])


@router.get(
    "",
    response_model=ApiResponse[list[SuperadminAuditLogResponse]],
    summary="List tenant audit logs",
    description="Returns the most recent audit log entries for the active tenant, with optional filters.",
)
async def list_audit_logs(
    context: TenantContext = Depends(require_permission(Permission.VIEW_LOGS)),
    connection: AsyncConnection = Depends(get_connection),
    limit: int = Query(100, ge=1, le=500),
    started_at: datetime | None = Query(None),
    ended_at: datetime | None = Query(None),
    action: str | None = Query(None),
    resource: str | None = Query(None),
) -> ApiResponse[list[SuperadminAuditLogResponse]]:
    logs = await AuditLogRepository(connection).list_by_tenant(
        tenant_id=context.tenant_id,
        limit=limit,
        started_at=started_at,
        ended_at=ended_at,
        action=action,
        resource=resource,
    )
    return api_success(
        [
            SuperadminAuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                user_email=log.user_email,
                user_name=log.user_name,
                action=log.action,
                resource=log.resource,
                resource_id=log.resource_id,
                actor_type=log.actor_type,
                actor_role=log.actor_role,
                created_at=log.created_at,
                metadata=log.metadata,
            )
            for log in logs
        ]
    )
