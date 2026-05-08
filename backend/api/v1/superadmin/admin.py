from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection

from app.responses import api_success
from app.schemas import (
    ApiResponse,
    MessageResponse,
    SuperadminAgentInstanceResponse,
    SuperadminAuditLogResponse,
    SuperadminMemberAddRequest,
    SuperadminTenantCreateRequest,
    SuperadminTenantResponse,
    SuperadminTenantUpdateRequest,
    SuperadminUserResponse,
    SuperadminUserUpdateRequest,
    TenantMemberResponse,
    TenantMemberUpdateRequest,
)
from database.repositories.agent_instances import AgentInstanceRepository
from database.repositories.audit import AuditLogFullRecord, AuditLogRepository
from database.repositories.memberships import MembershipAdminRepository
from database.repositories.superadmin_admin import SuperadminAdminRepository, TenantAdminRecord, UserAdminRecord
from database.repositories.versions import ResourceVersionRepository
from dependencies.auth import CurrentUser, get_connection, require_superadmin


router = APIRouter(prefix="/superadmin", tags=["superadmin-admin"])
SENSITIVE_SETTING_KEYS = {"api_key", "apikey", "authorization", "password", "secret", "token"}


@router.get(
    "/tenants",
    response_model=ApiResponse[list[SuperadminTenantResponse]],
    summary="List tenants as superadmin",
    description="Lists all platform tenants for superadmin administration, including operational status and non-secret settings.",
)
async def list_tenants(
    _: CurrentUser = Depends(require_superadmin),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[list[SuperadminTenantResponse]]:
    tenants = await SuperadminAdminRepository(connection).list_tenants()
    return api_success([_tenant_response(item) for item in tenants])


@router.post(
    "/tenants",
    response_model=ApiResponse[SuperadminTenantResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create tenant as superadmin",
    description="Creates a platform tenant and records superadmin audit and version entries for the tenant-scoped change.",
)
async def create_tenant(
    payload: SuperadminTenantCreateRequest,
    actor: CurrentUser = Depends(require_superadmin),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[SuperadminTenantResponse]:
    _reject_sensitive_settings(payload.settings)
    repository = SuperadminAdminRepository(connection)
    try:
        tenant = await repository.create_tenant(**payload.model_dump())
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Tenant slug already exists") from exc
    await _record_tenant_mutation(
        connection=connection,
        actor=actor,
        tenant=tenant,
        action="tenant.created",
        metadata={"slug": tenant.slug},
    )
    return api_success(_tenant_response(tenant), message="Tenant created.")


@router.get(
    "/tenants/{tenant_id}",
    response_model=ApiResponse[SuperadminTenantResponse],
    summary="Get tenant as superadmin",
    description="Returns one platform tenant by ID for superadmin administration.",
)
async def get_tenant(
    tenant_id: UUID,
    _: CurrentUser = Depends(require_superadmin),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[SuperadminTenantResponse]:
    tenant = await SuperadminAdminRepository(connection).get_tenant(tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
    return api_success(_tenant_response(tenant))


@router.patch(
    "/tenants/{tenant_id}",
    response_model=ApiResponse[SuperadminTenantResponse],
    summary="Update tenant as superadmin",
    description="Updates tenant name, plan, status, or non-secret settings and records superadmin audit/version entries.",
)
async def update_tenant(
    tenant_id: UUID,
    payload: SuperadminTenantUpdateRequest,
    actor: CurrentUser = Depends(require_superadmin),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[SuperadminTenantResponse]:
    if payload.settings is not None:
        _reject_sensitive_settings(payload.settings)
    tenant = await SuperadminAdminRepository(connection).update_tenant(
        tenant_id=tenant_id,
        **payload.model_dump(exclude_unset=True),
    )
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
    await _record_tenant_mutation(
        connection=connection,
        actor=actor,
        tenant=tenant,
        action="tenant.updated",
        metadata=payload.model_dump(exclude_unset=True),
    )
    return api_success(_tenant_response(tenant), message="Tenant updated.")


@router.get(
    "/users",
    response_model=ApiResponse[list[SuperadminUserResponse]],
    summary="List users as superadmin",
    description="Lists global user accounts without password hashes, refresh tokens, or credential material.",
)
async def list_users(
    q: str | None = Query(default=None, max_length=160),
    status_filter: str | None = Query(default=None, alias="status", pattern=r"^(pending|active|suspended)$"),
    is_superadmin: bool | None = None,
    _: CurrentUser = Depends(require_superadmin),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[list[SuperadminUserResponse]]:
    users = await SuperadminAdminRepository(connection).list_users(
        query=q,
        status=status_filter,
        is_superadmin=is_superadmin,
    )
    return api_success([_user_response(item) for item in users])


@router.get(
    "/users/{user_id}",
    response_model=ApiResponse[SuperadminUserResponse],
    summary="Get user as superadmin",
    description="Returns one global user account without password hashes, refresh tokens, or credential material.",
)
async def get_user(
    user_id: UUID,
    _: CurrentUser = Depends(require_superadmin),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[SuperadminUserResponse]:
    user = await SuperadminAdminRepository(connection).get_user(user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return api_success(_user_response(user))


@router.patch(
    "/users/{user_id}",
    response_model=ApiResponse[SuperadminUserResponse],
    summary="Update user as superadmin",
    description="Updates safe global user fields. A superadmin cannot suspend or demote their own account.",
)
async def update_user(
    user_id: UUID,
    payload: SuperadminUserUpdateRequest,
    actor: CurrentUser = Depends(require_superadmin),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[SuperadminUserResponse]:
    if user_id == actor.id and (payload.status == "suspended" or payload.is_superadmin is False):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Superadmin cannot suspend or demote own account")
    user = await SuperadminAdminRepository(connection).update_user(
        user_id=user_id,
        **payload.model_dump(exclude_unset=True),
    )
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    await AuditLogRepository(connection).record(
        tenant_id=None,
        user_id=actor.id,
        actor_type="superadmin",
        actor_role="superadmin",
        action="user.updated",
        resource="users",
        resource_id=str(user.id),
        metadata=payload.model_dump(exclude_unset=True),
    )
    return api_success(_user_response(user), message="User updated.")


@router.get(
    "/tenants/{tenant_id}/members",
    response_model=ApiResponse[list[TenantMemberResponse]],
    summary="List tenant members as superadmin",
    description="Lists explicit members of the given tenant, including superadmins assigned as tenant members.",
)
async def list_tenant_members(
    tenant_id: UUID,
    _: CurrentUser = Depends(require_superadmin),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[list[TenantMemberResponse]]:
    members = await MembershipAdminRepository(connection).list_members(
        tenant_id=tenant_id, include_superadmins=True
    )
    return api_success([_member_response(m) for m in members])


@router.delete(
    "/tenants/{tenant_id}/members/{user_id}",
    response_model=ApiResponse[MessageResponse],
    summary="Remove tenant member as superadmin",
    description="Removes a member from a tenant. Records audit log.",
)
async def remove_tenant_member(
    tenant_id: UUID,
    user_id: UUID,
    actor: CurrentUser = Depends(require_superadmin),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[MessageResponse]:
    member = await MembershipAdminRepository(connection).delete_member(
        tenant_id=tenant_id, user_id=user_id, include_superadmins=True
    )
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant member not found")
    await connection.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        {"tid": str(tenant_id)},
    )
    await AuditLogRepository(connection).record(
        tenant_id=tenant_id,
        user_id=actor.id,
        actor_type="superadmin",
        actor_role="superadmin",
        action="membership.removed",
        resource="memberships",
        resource_id=str(user_id),
    )
    return api_success(MessageResponse(message="Member removed."), message="Member removed.")


@router.post(
    "/tenants/{tenant_id}/members",
    response_model=ApiResponse[TenantMemberResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add member to tenant as superadmin",
    description="Looks up user by email and upserts an active membership with the given role.",
)
async def add_tenant_member(
    tenant_id: UUID,
    payload: SuperadminMemberAddRequest,
    actor: CurrentUser = Depends(require_superadmin),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[TenantMemberResponse]:
    users = await SuperadminAdminRepository(connection).list_users(query=payload.email)
    user = next((u for u in users if u.email.lower() == payload.email.lower()), None)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    member = await MembershipAdminRepository(connection).upsert_active_member(
        tenant_id=tenant_id,
        user_id=user.id,
        role=payload.role,
        invited_by=actor.id,
        include_superadmins=True,
    )
    if member is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to add member")
    await connection.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        {"tid": str(tenant_id)},
    )
    await AuditLogRepository(connection).record(
        tenant_id=tenant_id,
        user_id=actor.id,
        actor_type="superadmin",
        actor_role="superadmin",
        action="membership.added",
        resource="memberships",
        resource_id=str(user.id),
        metadata={"role": payload.role, "email": payload.email},
    )
    return api_success(_member_response(member), message="Member added.")


@router.patch(
    "/tenants/{tenant_id}/members/{user_id}",
    response_model=ApiResponse[TenantMemberResponse],
    summary="Update tenant member as superadmin",
    description="Updates role or status of an existing tenant member.",
)
async def update_tenant_member(
    tenant_id: UUID,
    user_id: UUID,
    payload: TenantMemberUpdateRequest,
    actor: CurrentUser = Depends(require_superadmin),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[TenantMemberResponse]:
    if payload.role is None and payload.status is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No changes provided")
    member = await MembershipAdminRepository(connection).update_member(
        tenant_id=tenant_id,
        user_id=user_id,
        role=payload.role,
        status=payload.status,
        include_superadmins=True,
    )
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant member not found")
    await connection.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        {"tid": str(tenant_id)},
    )
    await AuditLogRepository(connection).record(
        tenant_id=tenant_id,
        user_id=actor.id,
        actor_type="superadmin",
        actor_role="superadmin",
        action="membership.updated",
        resource="memberships",
        resource_id=str(user_id),
        metadata=payload.model_dump(exclude_unset=True),
    )
    return api_success(_member_response(member), message="Member updated.")


@router.get(
    "/tenants/{tenant_id}/instances",
    response_model=ApiResponse[list[SuperadminAgentInstanceResponse]],
    summary="List tenant agent instances as superadmin",
    description="Lists all agent instances for the given tenant.",
)
async def list_tenant_instances(
    tenant_id: UUID,
    _: CurrentUser = Depends(require_superadmin),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[list[SuperadminAgentInstanceResponse]]:
    instances = await AgentInstanceRepository(connection).list_instances(tenant_id=tenant_id)
    return api_success([
        SuperadminAgentInstanceResponse(
            id=i.id,
            name=i.name,
            description=i.description,
            model=i.model,
            status=i.status,
        )
        for i in instances
    ])


@router.get(
    "/tenants/{tenant_id}/audit",
    response_model=ApiResponse[list[SuperadminAuditLogResponse]],
    summary="List tenant audit log as superadmin",
    description="Returns the 100 most recent audit log entries for the given tenant.",
)
async def list_tenant_audit(
    tenant_id: UUID,
    _: CurrentUser = Depends(require_superadmin),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[list[SuperadminAuditLogResponse]]:
    logs = await AuditLogRepository(connection).list_by_tenant(tenant_id=tenant_id)
    return api_success([_audit_response(log) for log in logs])


async def _record_tenant_mutation(
    *,
    connection: AsyncConnection,
    actor: CurrentUser,
    tenant: TenantAdminRecord,
    action: str,
    metadata: dict,
) -> None:
    await connection.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant.id)},
    )
    await AuditLogRepository(connection).record(
        tenant_id=tenant.id,
        user_id=actor.id,
        actor_type="superadmin",
        actor_role="superadmin",
        action=action,
        resource="tenants",
        resource_id=str(tenant.id),
        metadata=metadata,
    )
    await ResourceVersionRepository(connection).record(
        tenant_id=tenant.id,
        changed_by=actor.id,
        actor_type="superadmin",
        actor_role="superadmin",
        action=action,
        resource="tenants",
        resource_id=str(tenant.id),
        snapshot=_tenant_response(tenant).model_dump(mode="json"),
        metadata=metadata,
    )


def _reject_sensitive_settings(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = key.lower().replace("-", "_")
            if normalized in SENSITIVE_SETTING_KEYS:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Sensitive tenant setting is not allowed: {key}")
            _reject_sensitive_settings(item)
    elif isinstance(value, list):
        for item in value:
            _reject_sensitive_settings(item)


def _tenant_response(record: TenantAdminRecord) -> SuperadminTenantResponse:
    return SuperadminTenantResponse(
        id=record.id,
        slug=record.slug,
        name=record.name,
        plan=record.plan,
        status=record.status,
        settings=record.settings,
    )


def _user_response(record: UserAdminRecord) -> SuperadminUserResponse:
    return SuperadminUserResponse(
        id=record.id,
        email=record.email,
        name=record.name,
        status=record.status,
        is_superadmin=record.is_superadmin,
    )


def _member_response(record) -> TenantMemberResponse:
    return TenantMemberResponse(
        user_id=record.user_id,
        email=record.email,
        name=record.name,
        role=record.role,
        status=record.status,
    )


def _audit_response(record: AuditLogFullRecord) -> SuperadminAuditLogResponse:
    return SuperadminAuditLogResponse(
        id=record.id,
        user_id=record.user_id,
        action=record.action,
        resource=record.resource,
        resource_id=record.resource_id,
        actor_type=record.actor_type,
        actor_role=record.actor_role,
        created_at=record.created_at,
    )
