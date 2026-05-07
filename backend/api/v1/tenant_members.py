from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.cache import redis_client
from app.rbac import Permission, Role
from app.responses import api_success
from app.schemas import ApiResponse, MessageResponse, TenantMemberResponse, TenantMemberUpdateRequest
from database.connection import TenantContext
from database.repositories.audit import AuditLogRepository
from database.repositories.memberships import MembershipAdminRepository, TenantMemberRecord
from database.repositories.versions import ResourceVersionRepository
from dependencies.auth import get_connection, require_permission


router = APIRouter(prefix="/tenant/members", tags=["tenant-members"])


@router.get(
    "",
    response_model=ApiResponse[list[TenantMemberResponse]],
    summary="List tenant members",
    description="Lists visible non-superadmin members for the selected tenant. Requires Bearer auth, X-Tenant-ID, and member-management permission.",
)
async def list_members(
    context: TenantContext = Depends(require_permission(Permission.INVITE_MEMBERS)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[list[TenantMemberResponse]]:
    members = await MembershipAdminRepository(connection).list_members(tenant_id=context.tenant_id)
    return api_success([_member_response(item) for item in members])


@router.patch(
    "/{user_id}",
    response_model=ApiResponse[TenantMemberResponse],
    summary="Update tenant member role or status",
    description="Updates a visible tenant member role or status, invalidates membership cache, and records tenant audit/version entries.",
)
async def update_member(
    user_id: UUID,
    payload: TenantMemberUpdateRequest,
    context: TenantContext = Depends(require_permission(Permission.INVITE_MEMBERS)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[TenantMemberResponse]:
    if payload.role is None and payload.status is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No membership changes provided")
    if context.user_id == user_id and context.role != Role.SUPERADMIN.value:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tenant admin cannot modify own membership")

    repository = MembershipAdminRepository(connection)
    member = await repository.update_member(
        tenant_id=context.tenant_id,
        user_id=user_id,
        role=payload.role,
        status=payload.status,
    )
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant member not found")
    await _after_membership_mutation(
        connection=connection,
        context=context,
        member=member,
        action="membership.updated",
        metadata=payload.model_dump(exclude_unset=True),
    )
    return api_success(_member_response(member), message="Tenant member updated.")


@router.delete(
    "/{user_id}",
    response_model=ApiResponse[MessageResponse],
    summary="Remove tenant member",
    description="Removes a visible tenant member from the selected tenant, invalidates membership cache, and records tenant audit/version entries.",
)
async def remove_member(
    user_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.INVITE_MEMBERS)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[MessageResponse]:
    if context.user_id == user_id and context.role != Role.SUPERADMIN.value:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tenant admin cannot remove own membership")
    member = await MembershipAdminRepository(connection).delete_member(tenant_id=context.tenant_id, user_id=user_id)
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant member not found")
    await _after_membership_mutation(
        connection=connection,
        context=context,
        member=member,
        action="membership.removed",
        metadata={"removed_user_id": str(user_id)},
    )
    message = "Tenant member removed."
    return api_success(MessageResponse(message=message), message=message)


async def _after_membership_mutation(
    *,
    connection: AsyncConnection,
    context: TenantContext,
    member: TenantMemberRecord,
    action: str,
    metadata: dict,
) -> None:
    await _invalidate_membership_cache(user_id=member.user_id, tenant_id=context.tenant_id)
    await connection.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(context.tenant_id)},
    )
    actor_type = "superadmin" if context.role == Role.SUPERADMIN.value else "user"
    actor_role = Role.SUPERADMIN.value if context.role == Role.SUPERADMIN.value else context.role
    await AuditLogRepository(connection).record(
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        actor_type=actor_type,
        actor_role=actor_role,
        action=action,
        resource="memberships",
        resource_id=str(member.user_id),
        metadata=metadata,
    )
    await ResourceVersionRepository(connection).record(
        tenant_id=context.tenant_id,
        changed_by=context.user_id,
        actor_type=actor_type,
        actor_role=actor_role,
        action=action,
        resource="memberships",
        resource_id=str(member.user_id),
        snapshot=_member_response(member).model_dump(mode="json"),
        metadata=metadata,
    )


async def _invalidate_membership_cache(*, user_id: UUID, tenant_id: UUID) -> None:
    try:
        await redis_client.delete(f"membership:{user_id}:{tenant_id}")
    except (RedisError, RuntimeError):
        pass


def _member_response(record: TenantMemberRecord) -> TenantMemberResponse:
    return TenantMemberResponse(
        user_id=record.user_id,
        email=record.email,
        name=record.name,
        role=record.role,
        status=record.status,
    )
