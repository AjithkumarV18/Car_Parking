from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any
from uuid import uuid4

import jwt
from jwt import InvalidTokenError
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.core.constants import TokenType
from app.core.exceptions import AuthenticationError


class Principal(BaseModel):
    """Identity claims available to authorization dependencies."""

    user_id: str
    company_id: str
    roles: set[str] = Field(default_factory=set)
    permissions: set[str] = Field(default_factory=set)
    is_super_admin: bool = False
    session_id: str | None = None
    token_type: TokenType = TokenType.ACCESS


def create_token(
    *,
    subject: str,
    company_id: str,
    roles: set[str] | None = None,
    permissions: set[str] | None = None,
    token_type: TokenType = TokenType.ACCESS,
    is_super_admin: bool = False,
    session_id: str | None = None,
    expires_in: timedelta | None = None,
    settings: Settings,
) -> str:
    """Create a signed JWT. Issuing tokens belongs to a future identity module."""

    lifetime = expires_in or (
        timedelta(minutes=settings.access_token_expire_minutes)
        if token_type is TokenType.ACCESS
        else timedelta(days=settings.refresh_token_expire_days)
    )
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "company_id": company_id,
        "roles": sorted(roles or set()),
        "permissions": sorted(permissions or set()),
        "token_type": token_type.value,
        "is_super_admin": is_super_admin,
        "jti": session_id or str(uuid4()),
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str, settings: Settings) -> Principal:
    """Verify a JWT and map its minimal claims to a framework-neutral principal."""

    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
        subject = payload.get("sub")
        company_id = payload.get("company_id")
        if not isinstance(subject, str) or not subject or not isinstance(company_id, str) or not company_id:
            raise AuthenticationError("Token identity claims are missing.")
        return Principal(
            user_id=subject,
            company_id=company_id,
            roles=set(payload.get("roles", [])),
            permissions=set(payload.get("permissions", [])),
            is_super_admin=bool(payload.get("is_super_admin", False)),
            session_id=payload.get("jti"),
            token_type=payload.get("token_type", TokenType.ACCESS),
        )
    except (InvalidTokenError, ValueError, TypeError) as exc:
        raise AuthenticationError("Invalid or expired access token.") from exc


def token_fingerprint(token: str) -> str:
    """One-way token fingerprint used for revocable-token persistence."""

    return sha256(token.encode("utf-8")).hexdigest()
