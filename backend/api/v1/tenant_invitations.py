from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.cache import redis_client
from app.config import settings
from app.rbac import Permission, Role
from app.responses import api_success
from app.schemas import (
    ApiResponse,
    MessageResponse,
    TenantInvitationAcceptRequest,
    TenantInvitationAcceptResponse,
    TenantInvitationCreateRequest,
    TenantInvitationPublicResponse,
    TenantInvitationResponse,
    TenantInvitationValidateRequest,
)
from app.security import create_action_token, hash_password, hash_token
from database.connection import TenantContext
from database.repositories.audit import AuditLogRepository
from database.repositories.auth_tokens import EmailEventRepository
from database.repositories.email_templates import EmailTemplateRepository
from database.repositories.invitations import InvitationRecord, InvitationRepository
from database.repositories.memberships import MembershipAdminRepository, TenantMemberRecord
from database.repositories.users import UserRecord, UserRepository
from database.repositories.versions import ResourceVersionRepository
from dependencies.auth import get_connection, require_permission


tenant_router = APIRouter(prefix="/tenant/invitations", tags=["tenant-invitations"])
public_router = APIRouter(prefix="/invitations", tags=["tenant-invitations"])


@tenant_router.get(
    "",
    response_model=ApiResponse[list[TenantInvitationResponse]],
    summary="List tenant invitations",
    description="Lists tenant invitations for the selected tenant. Requires Bearer auth, X-Tenant-ID, and member-management permission.",
)
async def list_invitations(
    context: TenantContext = Depends(require_permission(Permission.INVITE_MEMBERS)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[list[TenantInvitationResponse]]:
    records = await InvitationRepository(connection).list_for_tenant(tenant_id=context.tenant_id)
    return api_success([_invitation_response(record) for record in records])


@tenant_router.post(
    "",
    response_model=ApiResponse[TenantInvitationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create tenant invitation",
    description="Creates or refreshes a single-use tenant invitation, queues the tenant_invitation email template, and records tenant audit/version entries.",
)
async def create_invitation(
    payload: TenantInvitationCreateRequest,
    context: TenantContext = Depends(require_permission(Permission.INVITE_MEMBERS)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[TenantInvitationResponse]:
    record = await _create_or_refresh_invitation(
        connection=connection,
        context=context,
        email=str(payload.email),
        role=payload.role,
        action="invitation.created",
    )
    return api_success(_invitation_response(record), message="Tenant invitation created.")


@tenant_router.post(
    "/{invitation_id}/resend",
    response_model=ApiResponse[TenantInvitationResponse],
    summary="Resend tenant invitation",
    description="Refreshes an existing pending tenant invitation token, queues a new tenant_invitation email event, and records tenant audit/version entries.",
)
async def resend_invitation(
    invitation_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.INVITE_MEMBERS)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[TenantInvitationResponse]:
    repository = InvitationRepository(connection)
    existing = await repository.get_by_id(tenant_id=context.tenant_id, invitation_id=invitation_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant invitation not found")
    if existing.status == "accepted":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Accepted invitation cannot be resent")
    record = await _create_or_refresh_invitation(
        connection=connection,
        context=context,
        email=existing.email,
        role=existing.role,
        action="invitation.resent",
    )
    return api_success(_invitation_response(record), message="Tenant invitation resent.")


@tenant_router.delete(
    "/{invitation_id}",
    response_model=ApiResponse[MessageResponse],
    summary="Cancel tenant invitation",
    description="Cancels a pending tenant invitation and records tenant audit/version entries. Accepted, expired, or unknown invitations cannot be cancelled.",
)
async def cancel_invitation(
    invitation_id: UUID,
    context: TenantContext = Depends(require_permission(Permission.INVITE_MEMBERS)),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[MessageResponse]:
    record = await InvitationRepository(connection).cancel(tenant_id=context.tenant_id, invitation_id=invitation_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pending tenant invitation not found")
    await _record_invitation_change(
        connection=connection,
        context=context,
        record=record,
        action="invitation.cancelled",
        metadata={"email": record.email, "role": record.role},
    )
    message = "Tenant invitation cancelled."
    return api_success(MessageResponse(message=message), message=message)


@public_router.post(
    "/validate",
    response_model=ApiResponse[TenantInvitationPublicResponse],
    summary="Validate tenant invitation token",
    description="Validates a public tenant invitation token and returns non-secret invitation context for the invite acceptance screen.",
    responses={400: {"description": "Invitation token is invalid, expired, cancelled, or already accepted."}},
)
async def validate_invitation(
    payload: TenantInvitationValidateRequest,
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[TenantInvitationPublicResponse]:
    record = await _get_valid_invitation(connection=connection, token=payload.token)
    return api_success(_public_invitation_response(record))


@public_router.post(
    "/accept",
    response_model=ApiResponse[TenantInvitationAcceptResponse],
    summary="Accept tenant invitation",
    description="Consumes a valid tenant invitation token, creates or activates the invited account, creates active tenant membership, invalidates membership cache, and records tenant audit/version entries.",
    responses={400: {"description": "Invitation token or invited email is invalid, expired, cancelled, or already accepted."}},
)
async def accept_invitation(
    payload: TenantInvitationAcceptRequest,
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[TenantInvitationAcceptResponse]:
    token_hash = hash_token(payload.token)
    record = await _get_valid_invitation(connection=connection, token=payload.token)
    if record.email.lower() != str(payload.email).lower():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invitation email does not match")

    user = await _get_or_create_invited_user(connection=connection, payload=payload)
    accepted = await InvitationRepository(connection).mark_accepted(invitation_id=record.id, token_hash=token_hash)
    if accepted is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired tenant invitation")

    member = await MembershipAdminRepository(connection).upsert_active_member(
        tenant_id=record.tenant_id,
        user_id=user.id,
        role=record.role,
        invited_by=record.invited_by,
    )
    if member is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tenant invitation could not be accepted")

    context = TenantContext(tenant_id=record.tenant_id, user_id=user.id, role=record.role)
    await _after_membership_created(connection=connection, context=context, member=member, invitation=accepted)
    response = TenantInvitationAcceptResponse(
        user_id=user.id,
        tenant_id=record.tenant_id,
        email=user.email,
        role=record.role,
        membership_status=member.status,
    )
    return api_success(response, message="Tenant invitation accepted.")


async def _create_or_refresh_invitation(
    *,
    connection: AsyncConnection,
    context: TenantContext,
    email: str,
    role: str,
    action: str,
) -> InvitationRecord:
    user = await UserRepository(connection).get_by_email(email)
    if user is not None and user.is_superadmin:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Superadmin cannot be invited as a tenant member")
    if user is not None:
        member = await MembershipAdminRepository(connection).get_member(tenant_id=context.tenant_id, user_id=user.id)
        if member is not None and member.status == "active":
            raise HTTPException(status.HTTP_409_CONFLICT, "User is already an active tenant member")

    token, token_hash = create_action_token()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.action_token_expire_minutes)
    repository = InvitationRepository(connection)
    raw_record = await repository.create_or_refresh(
        tenant_id=context.tenant_id,
        email=email,
        role=role,
        token_hash=token_hash,
        invited_by=context.user_id,
        expires_at=expires_at,
    )
    record = await repository.get_by_id(tenant_id=context.tenant_id, invitation_id=raw_record.id)
    if record is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Tenant invitation could not be loaded")
    inviter_name = "Platform admin" if context.role == Role.SUPERADMIN.value else "Tenant admin"
    await _enqueue_invitation_email(connection=connection, record=record, token=token, inviter_name=inviter_name)
    await _record_invitation_change(
        connection=connection,
        context=context,
        record=record,
        action=action,
        metadata={"email": record.email, "role": record.role},
    )
    return record


async def _get_valid_invitation(*, connection: AsyncConnection, token: str) -> InvitationRecord:
    record = await InvitationRepository(connection).get_by_token_hash(token_hash=hash_token(token))
    if record is None or record.status != "pending" or record.accepted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired tenant invitation")
    if record.expires_at <= datetime.now(UTC):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired tenant invitation")
    return record


async def _get_or_create_invited_user(
    *,
    connection: AsyncConnection,
    payload: TenantInvitationAcceptRequest,
) -> UserRecord:
    repository = UserRepository(connection)
    user = await repository.get_by_email(str(payload.email))
    if user is not None and user.is_superadmin:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Superadmin cannot accept tenant invitations")
    if user is not None and user.status == "suspended":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is suspended")
    if user is None:
        if payload.password is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password is required for new invited accounts")
        return await repository.create_user(
            email=str(payload.email),
            name=payload.name,
            password_hash=hash_password(payload.password),
            status="active",
        )
    if user.status != "active":
        if user.password_hash is None and payload.password is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password is required for invited account activation")
        if user.password_hash is None and payload.password is not None:
            user = await repository.update_password_hash(user_id=user.id, password_hash=hash_password(payload.password))
            if user is None:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invited account could not be updated")
        activated = await repository.update_status(user_id=user.id, status="active")
        if activated is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invited account could not be activated")
        return activated
    return user


async def _enqueue_invitation_email(
    *,
    connection: AsyncConnection,
    record: InvitationRecord,
    token: str,
    inviter_name: str,
) -> None:
    template = await EmailTemplateRepository(connection).get_by_slug("tenant_invitation")
    if template is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Tenant invitation template not configured")
    await EmailEventRepository(connection).create(
        template_id=template.id,
        recipient_email=record.email,
        payload={
            "invitee_email": record.email,
            "inviter_name": inviter_name,
            "tenant_name": record.tenant_name or str(record.tenant_id),
            "role": record.role,
            "invitation_url": f"{settings.app_public_url.rstrip('/')}/accept-invitation?token={token}",
            "expires_in": f"{settings.action_token_expire_minutes} minutes",
        },
    )


async def _after_membership_created(
    *,
    connection: AsyncConnection,
    context: TenantContext,
    member: TenantMemberRecord,
    invitation: InvitationRecord,
) -> None:
    await _invalidate_membership_cache(user_id=member.user_id, tenant_id=context.tenant_id)
    await _record_invitation_change(
        connection=connection,
        context=context,
        record=invitation,
        action="invitation.accepted",
        metadata={"email": invitation.email, "role": invitation.role, "user_id": str(member.user_id)},
    )
    await _record_membership_version(
        connection=connection,
        context=context,
        member=member,
        invitation=invitation,
    )


async def _record_invitation_change(
    *,
    connection: AsyncConnection,
    context: TenantContext,
    record: InvitationRecord,
    action: str,
    metadata: dict,
) -> None:
    await connection.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(context.tenant_id)},
    )
    actor_type = "superadmin" if context.role == Role.SUPERADMIN.value else "user"
    actor_role = Role.SUPERADMIN.value if context.role == Role.SUPERADMIN.value else context.role
    snapshot = _invitation_response(record).model_dump(mode="json")
    await AuditLogRepository(connection).record(
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        actor_type=actor_type,
        actor_role=actor_role,
        action=action,
        resource="invitations",
        resource_id=str(record.id),
        metadata=metadata,
    )
    await ResourceVersionRepository(connection).record(
        tenant_id=context.tenant_id,
        changed_by=context.user_id,
        actor_type=actor_type,
        actor_role=actor_role,
        action=action,
        resource="invitations",
        resource_id=str(record.id),
        snapshot=snapshot,
        metadata=metadata,
    )


async def _record_membership_version(
    *,
    connection: AsyncConnection,
    context: TenantContext,
    member: TenantMemberRecord,
    invitation: InvitationRecord,
) -> None:
    snapshot = {
        "user_id": str(member.user_id),
        "email": member.email,
        "name": member.name,
        "role": member.role,
        "status": member.status,
    }
    metadata = {"invitation_id": str(invitation.id), "email": invitation.email, "role": invitation.role}
    await AuditLogRepository(connection).record(
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        actor_type="user",
        actor_role=context.role,
        action="membership.invitation_accepted",
        resource="memberships",
        resource_id=str(member.user_id),
        metadata=metadata,
    )
    await ResourceVersionRepository(connection).record(
        tenant_id=context.tenant_id,
        changed_by=context.user_id,
        actor_type="user",
        actor_role=context.role,
        action="membership.invitation_accepted",
        resource="memberships",
        resource_id=str(member.user_id),
        snapshot=snapshot,
        metadata=metadata,
    )


async def _invalidate_membership_cache(*, user_id: UUID, tenant_id: UUID) -> None:
    try:
        await redis_client.delete(f"membership:{user_id}:{tenant_id}")
    except (RedisError, RuntimeError):
        pass


def _invitation_response(record: InvitationRecord) -> TenantInvitationResponse:
    return TenantInvitationResponse(
        id=record.id,
        tenant_id=record.tenant_id,
        email=record.email,
        role=record.role,
        status=record.status,
        expires_at=record.expires_at,
        accepted_at=record.accepted_at,
        created_at=record.created_at,
    )


def _public_invitation_response(record: InvitationRecord) -> TenantInvitationPublicResponse:
    return TenantInvitationPublicResponse(
        tenant_id=record.tenant_id,
        tenant_name=record.tenant_name or str(record.tenant_id),
        email=record.email,
        role=record.role,
        status=record.status,
        expires_at=record.expires_at,
    )
