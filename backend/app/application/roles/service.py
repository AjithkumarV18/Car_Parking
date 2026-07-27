from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.exceptions import ConflictError, NotFoundError


def _role_code(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:40] or "custom_role"


class RoleService:
    """Manages reusable system templates and tenant-specific role definitions."""

    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.database = database

    async def _permission_map(self) -> dict[ObjectId, dict[str, Any]]:
        return {document["_id"]: document async for document in self.database.permissions.find({"status": "active"})}

    async def _resolve_permission_ids(self, keys: list[str]) -> list[ObjectId]:
        unique_keys = set(keys)
        permissions = await self.database.permissions.find(
            {"key": {"$in": list(unique_keys)}, "status": "active"}
        ).to_list(None)
        if len(permissions) != len(unique_keys):
            raise NotFoundError("One or more selected permissions do not exist or are inactive.")
        lookup = {permission["key"]: permission["_id"] for permission in permissions}
        return [lookup[key] for key in sorted(unique_keys)]

    async def _public_role(
        self,
        document: dict[str, Any],
        permission_map: dict[ObjectId, dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "id": str(document["_id"]),
            "company_id": str(document["company_id"]) if document.get("company_id") else None,
            "scope": document["scope"],
            "code": document["code"],
            "name": document["name"],
            "description": document.get("description"),
            "is_system": bool(document.get("is_system", False)),
            "status": document["status"],
            "permissions": [
                {
                    "key": permission_map[permission_id]["key"],
                    "name": permission_map[permission_id]["name"],
                    "module": permission_map[permission_id].get("module", "general"),
                    "action": permission_map[permission_id].get("action", "details"),
                }
                for permission_id in document.get("permission_ids", [])
                if permission_id in permission_map
            ],
        }

    async def list_permissions(self) -> list[dict[str, str]]:
        cursor = self.database.permissions.find({"status": "active"}).sort([("module", 1), ("action", 1)])
        return [
            {
                "key": document["key"],
                "name": document["name"],
                "module": document.get("module", "general"),
                "action": document.get("action", "details"),
            }
            async for document in cursor
        ]

    async def list_roles(self, company_id: str) -> list[dict[str, Any]]:
        identifier = ObjectId(company_id)
        permission_map = await self._permission_map()
        cursor = self.database.roles.find(
            {"status": "active", "$or": [{"scope": "system"}, {"scope": "company", "company_id": identifier}]}
        ).sort([("is_system", -1), ("name", 1)])
        return [await self._public_role(document, permission_map) async for document in cursor]

    async def get_role(self, company_id: str, role_id: str) -> dict[str, Any]:
        if not ObjectId.is_valid(role_id):
            raise NotFoundError("Role was not found.")
        document = await self.database.roles.find_one(
            {
                "_id": ObjectId(role_id),
                "status": "active",
                "$or": [{"scope": "system"}, {"scope": "company", "company_id": ObjectId(company_id)}],
            }
        )
        if not document:
            raise NotFoundError("Role was not found.")
        return await self._public_role(document, await self._permission_map())

    async def create_role(
        self, company_id: str, name: str, description: str | None, permission_keys: list[str], actor_id: str
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        document = {
            "scope": "company",
            "company_id": ObjectId(company_id),
            "code": _role_code(name),
            "name": name.strip(),
            "description": description.strip() if description else None,
            "permission_ids": await self._resolve_permission_ids(permission_keys),
            "is_system": False,
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "created_by": ObjectId(actor_id),
            "updated_by": ObjectId(actor_id),
        }
        try:
            result = await self.database.roles.insert_one(document)
        except DuplicateKeyError as exc:
            raise ConflictError("A role with this name already exists for this company.") from exc
        document["_id"] = result.inserted_id
        return await self._public_role(document, await self._permission_map())

    async def update_role(
        self,
        company_id: str,
        role_id: str,
        name: str | None,
        description: str | None,
        permission_keys: list[str] | None,
        actor_id: str,
    ) -> dict[str, Any]:
        if not ObjectId.is_valid(role_id):
            raise NotFoundError("Role was not found.")
        changes: dict[str, Any] = {"updated_at": datetime.now(UTC), "updated_by": ObjectId(actor_id)}
        if name is not None:
            changes.update({"name": name.strip(), "code": _role_code(name)})
        if description is not None:
            changes["description"] = description.strip() or None
        if permission_keys is not None:
            changes["permission_ids"] = await self._resolve_permission_ids(permission_keys)
        try:
            document = await self.database.roles.find_one_and_update(
                {
                    "_id": ObjectId(role_id),
                    "status": "active",
                    "$or": [
                        {"scope": "system", "is_system": True, "company_id": None},
                        {"scope": "company", "is_system": False, "company_id": ObjectId(company_id)},
                    ],
                },
                {"$set": changes},
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError as exc:
            raise ConflictError("A role with this name already exists for this company.") from exc
        if not document:
            raise NotFoundError("Role was not found or is inactive.")
        return await self._public_role(document, await self._permission_map())

    async def delete_role(self, company_id: str, role_id: str, actor_id: str) -> None:
        if not ObjectId.is_valid(role_id):
            raise NotFoundError("Role was not found.")
        identifier = ObjectId(role_id)
        assigned_user = await self.database.users.find_one(
            {"company_id": ObjectId(company_id), "role_ids": identifier, "status": "active"}
        )
        if assigned_user:
            raise ConflictError("Role is still assigned to an active user and cannot be deleted.")
        result = await self.database.roles.update_one(
            {
                "_id": identifier,
                "company_id": ObjectId(company_id),
                "scope": "company",
                "is_system": False,
                "status": "active",
            },
            {"$set": {"status": "inactive", "updated_at": datetime.now(UTC), "updated_by": ObjectId(actor_id)}},
        )
        if result.modified_count != 1:
            raise NotFoundError("Role was not found or is not deletable.")
