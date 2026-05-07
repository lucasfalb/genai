from collections.abc import Callable
import json
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncConnection

from app.cache import redis_client
from app.rbac import Permission, Role, has_permission
from app.security import AccessTokenClaims, create_access_token, decode_access_token
from database.connection import TenantContext, engine
from database.repositories.users import UserRepository


bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    id: UUID
    email: str
    is_superadmin: bool = False


async def get_connection():
    async with engine.begin() as connection:
        yield connection


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bearer token required")
    try:
        claims: AccessTokenClaims = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
    return CurrentUser(id=claims.sub, email=claims.email, is_superadmin=claims.is_superadmin)


async def get_tenant_context(
    x_tenant_id: str = Header(alias="X-Tenant-ID"),
    user: CurrentUser = Depends(get_current_user),
    connection: AsyncConnection = Depends(get_connection),
) -> TenantContext:
    if not x_tenant_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "X-Tenant-ID header required")

    try:
        tenant_id = UUID(x_tenant_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid X-Tenant-ID") from exc

    repository = UserRepository(connection)
    if user.is_superadmin:
        tenant_exists = await repository.tenant_exists(tenant_id)
        if not tenant_exists:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
        return TenantContext(tenant_id=tenant_id, user_id=user.id, role=Role.SUPERADMIN.value)

    cache_key = f"membership:{user.id}:{tenant_id}"
    try:
        cached = await redis_client.get(cache_key)
    except (RedisError, RuntimeError):
        cached = None

    if cached:
        payload = json.loads(cached)
        return TenantContext(tenant_id=tenant_id, user_id=user.id, role=payload["role"])

    membership = await repository.get_active_membership(user.id, tenant_id)
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this tenant")

    try:
        await redis_client.setex(cache_key, 300, json.dumps({"role": membership.role}))
    except (RedisError, RuntimeError):
        pass

    return TenantContext(tenant_id=tenant_id, user_id=user.id, role=membership.role)


def require_permission(permission: Permission) -> Callable:
    async def dependency(context: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        if not context.role or not has_permission(context.role, permission):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permission")
        return context

    return dependency


async def require_superadmin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.is_superadmin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Superadmin required")
    return user


def create_token_for_user(user: CurrentUser) -> str:
    return create_access_token(user_id=user.id, email=user.email, is_superadmin=user.is_superadmin)
