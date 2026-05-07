from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID
import hashlib
import secrets

import jwt
from pwdlib import PasswordHash
from pydantic import BaseModel

from app.config import settings


password_hash = PasswordHash.recommended()


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class ActionTokenType(StrEnum):
    ACCOUNT_ACTIVATION = "account_activation"
    PASSWORD_RESET = "password_reset"
    TENANT_INVITATION = "tenant_invitation"


class AccessTokenClaims(BaseModel):
    sub: UUID
    email: str
    is_superadmin: bool = False
    type: TokenType = TokenType.ACCESS
    exp: int


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, password_digest: str | None) -> bool:
    if not password_digest:
        return False
    return password_hash.verify(password, password_digest)


def create_access_token(*, user_id: UUID, email: str, is_superadmin: bool = False) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "email": email,
        "is_superadmin": is_superadmin,
        "type": TokenType.ACCESS.value,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> AccessTokenClaims:
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    return AccessTokenClaims.model_validate(payload)


def create_refresh_token() -> tuple[str, str, datetime]:
    token = secrets.token_urlsafe(48)
    token_hash = hash_token(token)
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    return token, token_hash, expires_at


def create_action_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(48)
    token_hash = hash_token(token)
    return token, token_hash


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
