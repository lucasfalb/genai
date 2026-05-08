from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection

from datetime import UTC, datetime, timedelta

from app.config import settings
from app.email_sender import dispatch_email
from app.responses import api_success
from app.schemas import (
    AccountActivationConfirmRequest,
    AccountActivationRequest,
    ApiResponse,
    AuthResponse,
    AuthMeResponse,
    LoginRequest,
    LogoutRequest,
    MembershipResponse,
    MessageResponse,
    PasswordChangeRequest,
    PasswordForgotRequest,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TenantAccessResponse,
    UserResponse,
)
from app.security import create_access_token, create_action_token, create_refresh_token, hash_password, hash_token, verify_password
from database.repositories.auth_tokens import AuthActionTokenRepository, EmailEventRepository
from database.repositories.email_templates import EmailTemplateRepository
from database.repositories.users import UserRepository
from dependencies.auth import CurrentUser, get_connection, get_current_user


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get(
    "/me",
    response_model=ApiResponse[AuthMeResponse],
    summary="Get authenticated user profile",
    description="Returns the global identity associated with the Bearer token without password hashes, credentials, or tenant-expanded data.",
)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[AuthMeResponse]:
    user = await UserRepository(connection).get_by_id(current_user.id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    return api_success(
        AuthMeResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            status=user.status,
            is_superadmin=user.is_superadmin,
        )
    )


@router.get(
    "/me/tenants",
    response_model=ApiResponse[list[TenantAccessResponse]],
    summary="List authenticated user tenant access",
    description="Returns real active tenant memberships for the Bearer token. Superadmin users are not represented as synthetic tenant members.",
)
async def get_my_tenants(
    current_user: CurrentUser = Depends(get_current_user),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[list[TenantAccessResponse]]:
    repository = UserRepository(connection)
    user = await repository.get_by_id(current_user.id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    memberships = await repository.list_tenant_access(user.id)
    return api_success(
        [
            TenantAccessResponse(
                tenant_id=item.tenant_id,
                tenant_slug=item.tenant_slug,
                tenant_name=item.tenant_name,
                role=item.role,
                status=item.status,
            )
            for item in memberships
        ]
    )


@router.post(
    "/logout",
    response_model=ApiResponse[MessageResponse],
    summary="Logout authenticated user",
    description="Revokes the provided refresh token for the Bearer token user, or all active refresh tokens for that user when no refresh token is provided.",
)
async def logout(
    payload: LogoutRequest,
    current_user: CurrentUser = Depends(get_current_user),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[MessageResponse]:
    repository = UserRepository(connection)
    user = await repository.get_by_id(current_user.id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    if payload.refresh_token:
        await repository.revoke_refresh_token(user_id=user.id, token_hash=hash_token(payload.refresh_token))
    else:
        await repository.revoke_refresh_tokens(user_id=user.id)
    message = "Logged out successfully."
    return api_success(MessageResponse(message=message), message=message)


@router.post(
    "/register",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a user account",
    description="Creates a pending user account with a hashed password. Email delivery is handled by a later provider integration.",
)
async def register(payload: RegisterRequest, connection: AsyncConnection = Depends(get_connection)) -> ApiResponse[UserResponse]:
    repository = UserRepository(connection)
    try:
        user = await repository.create_user(
            email=str(payload.email),
            name=payload.name,
            password_hash=hash_password(payload.password),
            status="pending",
        )
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from exc

    await _enqueue_activation_email(connection=connection, user=user)
    return api_success(
        UserResponse(id=user.id, email=user.email, name=user.name, status=user.status),
        message="Account registered. Activation is required before login.",
    )


@router.post(
    "/activation/request",
    response_model=ApiResponse[MessageResponse],
    summary="Request account activation email",
    description="Creates a new account activation token and queues an activation email when the account exists. The response is neutral to avoid email enumeration.",
)
async def request_activation(
    payload: AccountActivationRequest,
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[MessageResponse]:
    repository = UserRepository(connection)
    user = await repository.get_by_email(str(payload.email))
    if user is not None and user.status != "active":
        await _enqueue_activation_email(connection=connection, user=user)
    message = "If the account can be activated, an activation email will be sent."
    return api_success(MessageResponse(message=message), message=message)


@router.post(
    "/activation/confirm",
    response_model=ApiResponse[UserResponse],
    summary="Confirm account activation",
    description="Consumes a valid single-use activation token and marks the account as active.",
    responses={400: {"description": "Activation token is invalid, expired, or already used."}},
)
async def confirm_activation(
    payload: AccountActivationConfirmRequest,
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[UserResponse]:
    token_hash = hash_token(payload.token)
    token_record = await AuthActionTokenRepository(connection).consume(
        token_hash=token_hash,
        token_type="account_activation",
    )
    if token_record is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired activation token")

    user = await UserRepository(connection).update_status(user_id=token_record.user_id, status="active")
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid activation token")
    return api_success(
        UserResponse(id=user.id, email=user.email, name=user.name, status=user.status),
        message="Account activated.",
    )


@router.post(
    "/login",
    response_model=ApiResponse[AuthResponse],
    summary="Authenticate with email and password",
    description="Validates user credentials and returns access and refresh tokens when the user has tenant access or superadmin status.",
)
async def login(payload: LoginRequest, connection: AsyncConnection = Depends(get_connection)) -> ApiResponse[AuthResponse]:
    repository = UserRepository(connection)
    user = await repository.get_by_email(str(payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if user.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is not active")

    memberships = await repository.list_active_memberships(user.id)
    if not memberships and not user.is_superadmin:
        return api_success(
            AuthResponse(user_id=user.id, email=user.email, awaiting_assignment=True),
            message="Account authenticated but has no active tenant assignment.",
        )

    refresh_token, refresh_token_hash, expires_at = create_refresh_token()
    await repository.create_refresh_token(user_id=user.id, token_hash=refresh_token_hash, expires_at=expires_at)

    return api_success(
        AuthResponse(
            access_token=create_access_token(user_id=user.id, email=user.email, is_superadmin=user.is_superadmin),
            refresh_token=refresh_token,
            user_id=user.id,
            email=user.email,
            memberships=[MembershipResponse(tenant_id=item.tenant_id, role=item.role) for item in memberships],
        ),
        message="Authenticated.",
    )


async def _enqueue_activation_email(*, connection: AsyncConnection, user) -> None:
    token, token_hash = create_action_token()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.action_token_expire_minutes)
    await AuthActionTokenRepository(connection).invalidate_all_for_user(
        user_id=user.id,
        token_type="account_activation",
    )
    await AuthActionTokenRepository(connection).create(
        user_id=user.id,
        token_hash=token_hash,
        token_type="account_activation",
        expires_at=expires_at,
    )
    template = await EmailTemplateRepository(connection).get_by_slug("account_activation")
    if template is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Account activation template not configured")
    payload = {
        "platform_name": "GenAI",
        "user_name": user.name or user.email,
        "activation_url": f"{settings.app_public_url.rstrip('/')}/activation/confirm?token={token}",
        "expires_in": f"{settings.action_token_expire_minutes} minutes",
    }
    event = await EmailEventRepository(connection).create(
        template_id=template.id,
        recipient_email=user.email,
        payload=payload,
    )
    await dispatch_email(
        event_id=event.id,
        recipient_email=user.email,
        subject_template=template.subject_template,
        body_template=template.body_template,
        body_format=template.body_format,
        payload=payload,
        connection=connection,
    )


@router.post(
    "/password/forgot",
    response_model=ApiResponse[MessageResponse],
    summary="Request password reset email",
    description="Creates a single-use password reset token and queues a reset email when an active account exists. The response is neutral to avoid email enumeration.",
)
async def forgot_password(
    payload: PasswordForgotRequest,
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[MessageResponse]:
    repository = UserRepository(connection)
    user = await repository.get_by_email(str(payload.email))
    if user is not None and user.status == "active":
        await _enqueue_password_reset_email(connection=connection, user=user)
    message = "If the account can reset its password, a recovery email will be sent."
    return api_success(MessageResponse(message=message), message=message)


@router.post(
    "/password/reset",
    response_model=ApiResponse[MessageResponse],
    summary="Reset password with token",
    description="Consumes a valid single-use password reset token, updates the password hash, and revokes active refresh tokens.",
    responses={400: {"description": "Password reset token is invalid, expired, or already used."}},
)
async def reset_password(
    payload: PasswordResetRequest,
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[MessageResponse]:
    token_record = await AuthActionTokenRepository(connection).consume(
        token_hash=hash_token(payload.token),
        token_type="password_reset",
    )
    if token_record is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired password reset token")

    repository = UserRepository(connection)
    user = await repository.update_password_hash(
        user_id=token_record.user_id,
        password_hash=hash_password(payload.new_password),
    )
    if user is None or user.status != "active":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid password reset token")

    await repository.revoke_refresh_tokens(user_id=user.id)
    await _enqueue_password_changed_email(connection=connection, user=user)
    message = "Password reset successfully."
    return api_success(MessageResponse(message=message), message=message)


@router.post(
    "/password/change",
    response_model=ApiResponse[MessageResponse],
    summary="Change authenticated user password",
    description="Requires a Bearer token and current password, updates the password hash, and revokes active refresh tokens.",
    responses={401: {"description": "Bearer token is missing or invalid."}, 403: {"description": "Current password is invalid or account is inactive."}},
)
async def change_password(
    payload: PasswordChangeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    connection: AsyncConnection = Depends(get_connection),
) -> ApiResponse[MessageResponse]:
    repository = UserRepository(connection)
    user = await repository.get_by_id(current_user.id)
    if user is None or user.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is not active")
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Current password is invalid")

    updated_user = await repository.update_password_hash(user_id=user.id, password_hash=hash_password(payload.new_password))
    if updated_user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password could not be changed")
    await repository.revoke_refresh_tokens(user_id=user.id)
    await _enqueue_password_changed_email(connection=connection, user=updated_user)
    message = "Password changed successfully."
    return api_success(MessageResponse(message=message), message=message)


async def _enqueue_password_reset_email(*, connection: AsyncConnection, user) -> None:
    token, token_hash = create_action_token()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.action_token_expire_minutes)
    await AuthActionTokenRepository(connection).invalidate_all_for_user(
        user_id=user.id,
        token_type="password_reset",
    )
    await AuthActionTokenRepository(connection).create(
        user_id=user.id,
        token_hash=token_hash,
        token_type="password_reset",
        expires_at=expires_at,
    )
    template = await EmailTemplateRepository(connection).get_by_slug("password_reset")
    if template is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Password reset template not configured")
    payload = {
        "user_name": user.name or user.email,
        "reset_url": f"{settings.app_public_url.rstrip('/')}/reset-password?token={token}",
        "expires_in": f"{settings.action_token_expire_minutes} minutes",
    }
    event = await EmailEventRepository(connection).create(
        template_id=template.id,
        recipient_email=user.email,
        payload=payload,
    )
    await dispatch_email(
        event_id=event.id,
        recipient_email=user.email,
        subject_template=template.subject_template,
        body_template=template.body_template,
        body_format=template.body_format,
        payload=payload,
        connection=connection,
    )


async def _enqueue_password_changed_email(*, connection: AsyncConnection, user) -> None:
    template = await EmailTemplateRepository(connection).get_by_slug("password_changed")
    if template is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Password changed template not configured")
    payload = {
        "user_name": user.name or user.email,
        "changed_at": datetime.now(UTC).isoformat(),
    }
    event = await EmailEventRepository(connection).create(
        template_id=template.id,
        recipient_email=user.email,
        payload=payload,
    )
    await dispatch_email(
        event_id=event.id,
        recipient_email=user.email,
        subject_template=template.subject_template,
        body_template=template.body_template,
        body_format=template.body_format,
        payload=payload,
        connection=connection,
    )


@router.post(
    "/refresh",
    response_model=ApiResponse[AuthResponse],
    summary="Rotate refresh token",
    description="Consumes a valid refresh token, revokes it, and returns a new access token plus a rotated refresh token.",
)
async def refresh(payload: RefreshRequest, connection: AsyncConnection = Depends(get_connection)) -> ApiResponse[AuthResponse]:
    repository = UserRepository(connection)
    user = await repository.consume_refresh_token(token_hash=hash_token(payload.refresh_token))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    if user.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is not active")

    refresh_token, refresh_token_hash, expires_at = create_refresh_token()
    await repository.create_refresh_token(user_id=user.id, token_hash=refresh_token_hash, expires_at=expires_at)
    memberships = await repository.list_active_memberships(user.id)

    return api_success(
        AuthResponse(
            access_token=create_access_token(user_id=user.id, email=user.email, is_superadmin=user.is_superadmin),
            refresh_token=refresh_token,
            user_id=user.id,
            email=user.email,
            memberships=[MembershipResponse(tenant_id=item.tenant_id, role=item.role) for item in memberships],
        ),
        message="Token refreshed.",
    )
