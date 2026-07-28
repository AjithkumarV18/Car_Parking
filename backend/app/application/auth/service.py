from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pwdlib import PasswordHash

from app.core.config import Settings
from app.core.constants import TokenType
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.security import create_token, decode_token, token_fingerprint

password_hasher = PasswordHash.recommended()


class AuthService:
    """Tenant-aware identity operations with revocable, rotating refresh sessions."""

    def __init__(self, database: AsyncIOMotorDatabase, settings: Settings) -> None:
        self.database = database
        self.settings = settings

    async def _company_exists(self, company_id: str) -> None:
        if not await self.database.companies.find_one({"_id": ObjectId(company_id), "status": "active"}):
            raise NotFoundError("The requested company does not exist or is inactive.")

    async def _resolve_access(self, user: dict[str, Any]) -> tuple[set[str], set[str]]:
        role_ids = user.get("role_ids", [])
        if not role_ids:
            return set(), set()
        roles = await self.database.roles.find(
            {"_id": {"$in": role_ids}, "status": "active"}
        ).to_list(length=None)
        permission_ids = {permission_id for role in roles for permission_id in role.get("permission_ids", [])}
        permissions = await self.database.permissions.find(
            {"_id": {"$in": list(permission_ids)}, "status": "active"}
        ).to_list(length=None)
        return {role["code"] for role in roles}, {permission["key"] for permission in permissions}

    async def _issue_tokens(self, user: dict[str, Any], remember_me: bool) -> dict[str, Any]:
        roles, permissions = await self._resolve_access(user)
        company_id = str(user["company_id"])
        is_super_admin = bool(user.get("is_super_admin", False))
        session_id = str(uuid4())
        refresh_lifetime = timedelta(
            days=(
                self.settings.remember_me_refresh_token_expire_days
                if remember_me
                else self.settings.refresh_token_expire_days
            )
        )
        access_token = create_token(
            subject=str(user["_id"]),
            company_id=company_id,
            roles=roles,
            permissions=permissions,
            is_super_admin=is_super_admin,
            settings=self.settings,
        )
        refresh_token = create_token(
            subject=str(user["_id"]),
            company_id=company_id,
            token_type=TokenType.REFRESH,
            is_super_admin=is_super_admin,
            session_id=session_id,
            expires_in=refresh_lifetime,
            settings=self.settings,
        )
        now = datetime.now(UTC)
        await self.database.auth_sessions.insert_one(
            {
                "session_id": session_id,
                "user_id": user["_id"],
                "company_id": user["company_id"],
                "token_hash": token_fingerprint(refresh_token),
                "remember_me": remember_me,
                "status": "active",
                "created_at": now,
                "expires_at": now + refresh_lifetime,
                "revoked_at": None,
            }
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.settings.access_token_expire_minutes * 60,
            "user": await self._public_user(user, roles, permissions),
        }

    async def _public_user(self, user: dict[str, Any], roles: set[str], permissions: set[str]) -> dict[str, Any]:
        company = await self.database.companies.find_one({"_id": user["company_id"], "status": "active"})
        employee = await self.database.employees.find_one(
            {"company_id": user["company_id"], "user_id": user["_id"], "status": {"$ne": "inactive"}}
        )
        company_theme = company.get("theme", {}) if company else {}
        return {
            "id": str(user["_id"]),
            "company_id": str(user["company_id"]),
            "email": user["email"],
            "display_name": user["display_name"],
            "username": user.get("username"),
            "photo_url": employee.get("photo_url") if employee else None,
            "company_name": company.get("company_name") if company else None,
            "company_logo_url": company.get("logo_url") if company else None,
            "company_theme": {
                "primary_color": company_theme.get("primary_color", "#0B4F6C"),
                "secondary_color": company_theme.get("secondary_color", "#EF8354"),
            } if company else None,
            "roles": sorted(roles),
            "permissions": sorted(permissions),
            "is_super_admin": bool(user.get("is_super_admin", False)),
        }

    async def register(
        self,
        company_id: str,
        *,
        email: str,
        password: str,
        display_name: str,
        username: str,
        remember_me: bool,
    ) -> dict[str, Any]:
        await self._company_exists(company_id)
        normalized_email = email.lower().strip()
        normalized_username = username.lower().strip()
        if await self.database.users.find_one({"$or": [{"email": normalized_email}, {"username": normalized_username}]}):
            raise ConflictError("An account with this email or username already exists.")
        viewer_role = await self.database.roles.find_one(
            {"scope": "system", "company_id": None, "code": "viewer", "status": "active"}
        )
        now = datetime.now(UTC)
        user = {
            "company_id": ObjectId(company_id),
            "email": normalized_email,
            "username": normalized_username,
            "password_hash": password_hasher.hash(password),
            "display_name": display_name.strip(),
            "status": "active",
            "role_ids": [viewer_role["_id"]] if viewer_role else [],
            "is_super_admin": False,
            "created_at": now,
            "updated_at": now,
        }
        result = await self.database.users.insert_one(user)
        user["_id"] = result.inserted_id
        return await self._issue_tokens(user, remember_me)

    async def login(self, company_id: str, *, username: str, password: str, remember_me: bool) -> dict[str, Any]:
        await self._company_exists(company_id)
        identifier = username.lower().strip()
        user = await self.database.users.find_one({"$or": [{"username": identifier}, {"email": identifier}], "status": "active"})
        if not user or not password_hasher.verify(password, user["password_hash"]):
            raise AuthenticationError("Invalid username or password.")
        if not user.get("is_super_admin", False) and str(user["company_id"]) != company_id:
            raise AuthenticationError("Invalid username or password.")
        await self.database.users.update_one({"_id": user["_id"]}, {"$set": {"last_login_at": datetime.now(UTC)}})
        token_user = {**user, "company_id": ObjectId(company_id)} if user.get("is_super_admin", False) else user
        return await self._issue_tokens(token_user, remember_me)

    async def refresh(self, company_id: str, refresh_token: str) -> dict[str, Any]:
        principal = decode_token(refresh_token, self.settings)
        if principal.token_type is not TokenType.REFRESH or not principal.session_id:
            raise AuthenticationError("A refresh token is required.")
        if not principal.is_super_admin and principal.company_id != company_id:
            raise AuthenticationError("Refresh token company does not match request company.")
        session = await self.database.auth_sessions.find_one(
            {
                "session_id": principal.session_id,
                "token_hash": token_fingerprint(refresh_token),
                "status": "active",
                "expires_at": {"$gt": datetime.now(UTC)},
            }
        )
        if not session:
            raise AuthenticationError("Refresh token is invalid or has been revoked.")
        user = await self.database.users.find_one({"_id": session["user_id"], "status": "active"})
        if not user:
            raise AuthenticationError("User account is unavailable.")
        result = await self.database.auth_sessions.update_one(
            {"_id": session["_id"], "status": "active"},
            {"$set": {"status": "rotated", "revoked_at": datetime.now(UTC)}},
        )
        if result.modified_count != 1:
            raise AuthenticationError("Refresh token has already been used.")
        token_user = {**user, "company_id": session["company_id"]} if user.get("is_super_admin", False) else user
        return await self._issue_tokens(token_user, bool(session.get("remember_me", False)))

    async def get_profile(self, user_id: str, company_id: str | None = None) -> dict[str, Any]:
        user = await self.database.users.find_one({"_id": ObjectId(user_id), "status": "active"})
        if not user:
            raise AuthenticationError("User account is unavailable.")
        roles, permissions = await self._resolve_access(user)
        if company_id and ObjectId.is_valid(company_id):
            user = {**user, "company_id": ObjectId(company_id)}
        return await self._public_user(user, roles, permissions)

    async def request_password_reset(self, company_id: str, email: str) -> str | None:
        await self._company_exists(company_id)
        user = await self.database.users.find_one(
            {"email": email.lower().strip(), "company_id": ObjectId(company_id), "status": "active"}
        )
        if not user:
            return None
        session_id = str(uuid4())
        token = create_token(
            subject=str(user["_id"]),
            company_id=company_id,
            token_type=TokenType.PASSWORD_RESET,
            session_id=session_id,
            expires_in=timedelta(minutes=self.settings.password_reset_token_expire_minutes),
            settings=self.settings,
        )
        now = datetime.now(UTC)
        await self.database.password_reset_tokens.update_many(
            {"user_id": user["_id"], "used_at": None},
            {"$set": {"used_at": now}},
        )
        await self.database.password_reset_tokens.insert_one(
            {
                "session_id": session_id,
                "user_id": user["_id"],
                "company_id": user["company_id"],
                "token_hash": token_fingerprint(token),
                "expires_at": now + timedelta(minutes=self.settings.password_reset_token_expire_minutes),
                "used_at": None,
                "created_at": now,
            }
        )
        return token

    async def reset_password(self, company_id: str, token: str, new_password: str) -> None:
        principal = decode_token(token, self.settings)
        if principal.token_type is not TokenType.PASSWORD_RESET or not principal.session_id:
            raise AuthenticationError("Invalid password reset token.")
        if principal.company_id != company_id:
            raise AuthenticationError("Password reset token company does not match request company.")
        now = datetime.now(UTC)
        record = await self.database.password_reset_tokens.find_one_and_update(
            {
                "session_id": principal.session_id,
                "token_hash": token_fingerprint(token),
                "company_id": ObjectId(company_id),
                "used_at": None,
                "expires_at": {"$gt": now},
            },
            {"$set": {"used_at": now}},
        )
        if not record:
            raise AuthenticationError("Password reset token is invalid, expired, or already used.")
        await self.database.users.update_one(
            {"_id": record["user_id"]},
            {"$set": {"password_hash": password_hasher.hash(new_password), "updated_at": now}},
        )
        await self.database.auth_sessions.update_many(
            {"user_id": record["user_id"], "status": "active"},
            {"$set": {"status": "revoked", "revoked_at": now}},
        )
