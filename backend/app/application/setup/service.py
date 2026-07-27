from __future__ import annotations

from datetime import UTC, datetime, time
from decimal import Decimal
from hashlib import sha256
from hmac import compare_digest
from secrets import token_urlsafe
from typing import Any

from bson import ObjectId
from bson.decimal128 import Decimal128
from motor.motor_asyncio import AsyncIOMotorDatabase
from pwdlib import PasswordHash
from pymongo.errors import DuplicateKeyError

from app.core.exceptions import ConflictError, NotFoundError

password_hasher = PasswordHash.recommended()
_SETUP_ID = "initial_platform_setup"


def _code_from_name(name: str) -> str:
    import re

    code = re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")
    return code[:40] or "COMPANY"


class SetupService:
    """Creates the very first tenant and its first super-administrator exactly once."""

    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.database = database

    async def status(self) -> dict[str, Any]:
        setup = await self.database.platform_setup.find_one({"_id": _SETUP_ID})
        company = await self.database.companies.find_one({"status": "active"})
        if not company:
            if await self.database.companies.find_one({}):
                return {"step": "login", "company_id": None, "setup_required": False, "company": None}
            return {"step": "company", "company_id": None, "setup_required": True, "company": None}
        if setup and setup.get("state") in {"awaiting_admin", "creating_admin"}:
            return {"step": "employee", "company_id": str(setup["company_id"]), "setup_required": True, "company": self._public_branding(company)}
        return {"step": "login", "company_id": str(company["_id"]), "setup_required": False, "company": self._public_branding(company)}

    async def create_initial_company(self, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        if await self.database.companies.find_one({}):
            raise ConflictError("Initial setup is unavailable because a company record already exists.")

        now = datetime.now(UTC)
        try:
            await self.database.platform_setup.insert_one(
                {"_id": _SETUP_ID, "state": "creating_company", "created_at": now, "updated_at": now}
            )
        except DuplicateKeyError as exc:
            raise ConflictError("Initial setup is already in progress or has been completed.") from exc

        document = {
            **payload,
            "code": payload.get("code") or _code_from_name(payload["company_name"]),
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = await self.database.companies.insert_one(document)
        except DuplicateKeyError as exc:
            await self.database.platform_setup.delete_one({"_id": _SETUP_ID, "state": "creating_company"})
            raise ConflictError("A company with this code already exists.") from exc
        except Exception:
            await self.database.platform_setup.delete_one({"_id": _SETUP_ID, "state": "creating_company"})
            raise

        document["_id"] = result.inserted_id
        setup_token = token_urlsafe(32)
        await self.database.platform_setup.update_one(
            {"_id": _SETUP_ID, "state": "creating_company"},
            {
                "$set": {
                    "state": "awaiting_admin",
                    "company_id": result.inserted_id,
                    "setup_token_hash": sha256(setup_token.encode("utf-8")).hexdigest(),
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        return self._public_company(document), setup_token

    async def create_initial_employee(
        self,
        company_id: str,
        setup_token: str,
        payload: dict[str, Any],
    ) -> None:
        if not ObjectId.is_valid(company_id):
            raise NotFoundError("Setup company was not found.")
        company = ObjectId(company_id)
        token_hash = sha256(setup_token.encode("utf-8")).hexdigest()
        setup = await self.database.platform_setup.find_one({"_id": _SETUP_ID})
        if not setup or not compare_digest(str(setup.get("setup_token_hash", "")), token_hash):
            raise ConflictError("The setup session is invalid. Restart setup in the same browser.")
        if setup.get("company_id") != company:
            raise ConflictError("The setup session does not match this company.")

        claimed = await self.database.platform_setup.find_one_and_update(
            {"_id": _SETUP_ID, "state": "awaiting_admin", "setup_token_hash": token_hash},
            {"$set": {"state": "creating_admin", "updated_at": datetime.now(UTC)}},
        )
        if not claimed:
            raise ConflictError("The initial administrator is already being created or setup is complete.")

        user_id: ObjectId | None = None
        try:
            if not await self.database.companies.find_one({"_id": company, "status": "active"}):
                raise NotFoundError("Setup company was not found or is inactive.")
            if await self.database.users.find_one({"company_id": company}):
                raise ConflictError("The initial administrator has already been created.")
            role = await self.database.roles.find_one(
                {"scope": "system", "company_id": None, "code": "super_admin", "status": "active"}
            )
            if not role:
                raise NotFoundError("The Super Admin role is unavailable. Restart the API and try again.")

            now = datetime.now(UTC)
            user = {
                "company_id": company,
                "email": payload["email"].lower(),
                "username": payload["username"].lower(),
                "password_hash": password_hasher.hash(payload["password"]),
                "display_name": payload["name"],
                "status": "active",
                "role_ids": [role["_id"]],
                "is_super_admin": True,
                "created_at": now,
                "updated_at": now,
            }
            user_result = await self.database.users.insert_one(user)
            user_id = user_result.inserted_id
            employee = {
                "company_id": company,
                "user_id": user_result.inserted_id,
                "employee_id": payload["employee_id"].upper(),
                "photo_url": payload.get("photo_url"),
                "name": payload["name"],
                "gender": payload["gender"],
                "email": payload["email"].lower(),
                "phone": payload["phone"],
                "address": payload["address"],
                "designation": payload["designation"],
                "username": payload["username"].lower(),
                "role_id": role["_id"],
                "salary": Decimal128(str(Decimal(payload["salary"]))),
                "joining_date": datetime.combine(payload["joining_date"], time.min, tzinfo=UTC),
                "parking_location_id": None,
                "status": "active",
                "created_at": now,
                "updated_at": now,
                "created_by": user_result.inserted_id,
                "updated_by": user_result.inserted_id,
            }
            await self.database.employees.insert_one(employee)
        except Exception as exc:
            if user_id is not None:
                await self.database.users.delete_one({"_id": user_id})
            await self.database.platform_setup.update_one(
                {"_id": _SETUP_ID, "state": "creating_admin"},
                {"$set": {"state": "awaiting_admin", "updated_at": datetime.now(UTC)}},
            )
            if isinstance(exc, DuplicateKeyError):
                raise ConflictError("Employee ID, email, or username is already in use.") from exc
            raise

        await self.database.platform_setup.update_one(
            {"_id": _SETUP_ID, "state": "creating_admin"},
            {
                "$set": {"state": "complete", "completed_at": datetime.now(UTC), "updated_at": datetime.now(UTC)},
                "$unset": {"setup_token_hash": ""},
            },
        )

    @staticmethod
    def _public_company(document: dict[str, Any]) -> dict[str, Any]:
        public = {**document, "id": str(document["_id"])}
        public.pop("_id", None)
        return public

    @staticmethod
    def _public_branding(document: dict[str, Any]) -> dict[str, Any]:
        """The only company data exposed before authentication."""
        theme = document.get("theme") if isinstance(document.get("theme"), dict) else {}
        return {
            "id": str(document["_id"]),
            "company_name": document.get("company_name", ""),
            "logo_url": document.get("logo_url") or theme.get("logo_url"),
            "theme": {
                "primary_color": theme.get("primary_color", "#0B4F6C"),
                "secondary_color": theme.get("secondary_color", "#EF8354"),
            },
        }
