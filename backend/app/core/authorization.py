from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from bson import ObjectId
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import Principal
from app.core.tenant import get_company_id

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="bearerAuth")


async def get_current_principal(
    request: Request,
    _credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> Principal:
    """Resolve a live user, roles, and permissions before allowing a protected request."""

    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, Principal):
        raise AuthenticationError()
    if principal.token_type.value != "access":
        raise AuthenticationError("An access token is required.")
    if not ObjectId.is_valid(principal.user_id):
        raise AuthenticationError("Token subject is invalid.")
    database = request.app.state.mongo.database
    user = await database.users.find_one({"_id": ObjectId(principal.user_id), "status": "active"})
    if not user:
        raise AuthenticationError("User account is unavailable.")
    role_ids = user.get("role_ids", [])
    roles = await database.roles.find({"_id": {"$in": role_ids}, "status": "active"}).to_list(None)
    permission_ids = {permission_id for role in roles for permission_id in role.get("permission_ids", [])}
    permissions = await database.permissions.find(
        {"_id": {"$in": list(permission_ids)}, "status": "active"}
    ).to_list(None)
    requested_company_id = get_company_id(request)
    is_super_admin = bool(user.get("is_super_admin", False))
    principal = principal.model_copy(
        update={
            "company_id": requested_company_id if is_super_admin else str(user["company_id"]),
            "roles": {role["code"] for role in roles},
            "permissions": {permission["key"] for permission in permissions},
            "is_super_admin": is_super_admin,
        }
    )
    if not principal.is_super_admin and principal.company_id != requested_company_id:
        raise AuthorizationError("This user does not belong to the requested company.")
    return principal


def require_roles(*allowed_roles: str) -> Callable[..., Principal]:
    """Return a reusable FastAPI dependency that enforces any one allowed role."""

    allowed = set(allowed_roles)

    async def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.is_super_admin and not allowed.intersection(principal.roles):
            raise AuthorizationError("Your role is not allowed to perform this action.")
        return principal

    return dependency


def require_permissions(*required_permissions: str) -> Callable[..., Principal]:
    """Return a reusable dependency that requires all listed permissions."""

    required = set(required_permissions)

    async def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.is_super_admin and not required.issubset(principal.permissions):
            raise AuthorizationError("You are missing one or more required permissions.")
        return principal

    return dependency


def require_any_permissions(*allowed_permissions: str) -> Callable[..., Principal]:
    """Allow an operation when the user has at least one of the supplied permissions."""

    allowed = set(allowed_permissions)

    async def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.is_super_admin and not allowed.intersection(principal.permissions):
            raise AuthorizationError("You are missing permission to perform this action.")
        return principal

    return dependency


def require_super_admin() -> Callable[..., Principal]:
    """Restrict platform-management endpoints to a verified super administrator."""

    async def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.is_super_admin:
            raise AuthorizationError("Super administrator access is required.")
        return principal

    return dependency
