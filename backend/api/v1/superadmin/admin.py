from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection

from app.responses import api_success
from app.schemas import (
    ApiResponse,
    SuperadminTenantCreateRequest,
    SuperadminTenantResponse,
    SuperadminTenantUpdateRequest,
    SuperadminUserResponse,
    SuperadminUserUpdateRequest,
)
from database.repositories.audit import AuditLogRepository
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
