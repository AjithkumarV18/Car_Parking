from __future__ import annotations

from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Any

from bson import ObjectId
from bson.decimal128 import Decimal128
from motor.motor_asyncio import AsyncIOMotorDatabase
from pwdlib import PasswordHash
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.exceptions import ConflictError, NotFoundError
from app.shared.pagination import Page, PaginationParams

password_hasher = PasswordHash.recommended()


def _object_id(value: str, resource: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise NotFoundError(f"{resource} was not found.")
    return ObjectId(value)


class EmployeeService:
    """Tenant-scoped employee, linked-user, list, and export operations."""

    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.database = database

    async def _company(self, company_id: str) -> ObjectId:
        identifier = _object_id(company_id, "Company")
        if not await self.database.companies.find_one({"_id": identifier, "status": "active"}):
            raise NotFoundError("Company was not found or is inactive.")
        return identifier

    async def _role(self, company_id: ObjectId, role_id: str) -> dict[str, Any]:
        role = await self.database.roles.find_one(
            {
                "_id": _object_id(role_id, "Role"),
                "status": "active",
                "$or": [{"scope": "system"}, {"scope": "company", "company_id": company_id}],
            }
        )
        if not role:
            raise NotFoundError("Role was not found or is inactive.")
        return role

    async def _location(self, company_id: ObjectId, location_id: str | None) -> dict[str, Any] | None:
        if not location_id:
            return None
        location = await self.database.parking_locations.find_one(
            {"_id": _object_id(location_id, "Parking location"), "company_id": company_id, "status": "active"}
        )
        if not location:
            raise NotFoundError("Parking location was not found or is inactive.")
        return location

    @staticmethod
    def _as_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        return datetime.combine(value, time.min, tzinfo=UTC)

    async def _public(self, document: dict[str, Any]) -> dict[str, Any]:
        role = await self.database.roles.find_one({"_id": document["role_id"]})
        location = (
            await self.database.parking_locations.find_one({"_id": document["parking_location_id"]})
            if document.get("parking_location_id")
            else None
        )
        return {
            "id": str(document["_id"]),
            "employee_id": document["employee_id"],
            "photo_url": document.get("photo_url"),
            "name": document["name"],
            "gender": document["gender"],
            "email": document["email"],
            "phone": document["phone"],
            "address": document["address"],
            "designation": document["designation"],
            "username": document["username"],
            "role_id": str(document["role_id"]),
            "role_name": role["name"] if role else "Unknown role",
            "salary": str(document["salary"].to_decimal()),
            "joining_date": self._as_datetime(document["joining_date"]).date().isoformat(),
            "parking_location_id": str(document["parking_location_id"]) if document.get("parking_location_id") else None,
            "parking_location_name": location["name"] if location else None,
            "status": document["status"],
        }

    def _query(self, company_id: ObjectId, filters: dict[str, Any]) -> dict[str, Any]:
        query: dict[str, Any] = {"company_id": company_id, "status": {"$ne": "inactive"}}
        if filters.get("status"):
            query["status"] = filters["status"]
        if filters.get("gender"):
            query["gender"] = filters["gender"]
        if filters.get("role_id"):
            query["role_id"] = _object_id(filters["role_id"], "Role")
        if filters.get("parking_location_id"):
            query["parking_location_id"] = _object_id(filters["parking_location_id"], "Parking location")
        if search := filters.get("search"):
            pattern = {"$regex": search.strip(), "$options": "i"}
            query["$or"] = [{"employee_id": pattern}, {"name": pattern}, {"email": pattern}, {"designation": pattern}]
        return query

    async def list(self, company_id: str, pagination: PaginationParams, filters: dict[str, Any]) -> Page[dict[str, Any]]:
        identifier = await self._company(company_id)
        query = self._query(identifier, filters)
        sort_fields = {"employee_id", "name", "joining_date", "salary", "designation", "created_at"}
        sort_by = filters.get("sort_by") if filters.get("sort_by") in sort_fields else "name"
        direction = DESCENDING if filters.get("sort_order") == "desc" else ASCENDING
        total = await self.database.employees.count_documents(query)
        cursor = self.database.employees.find(query).sort(sort_by, direction).skip(pagination.offset).limit(pagination.limit)
        return Page.create(items=[await self._public(item) async for item in cursor], total=total, pagination=pagination)

    async def get(self, company_id: str, employee_id: str) -> dict[str, Any]:
        document = await self.database.employees.find_one(
            {"_id": _object_id(employee_id, "Employee"), "company_id": await self._company(company_id), "status": {"$ne": "inactive"}}
        )
        if not document:
            raise NotFoundError("Employee was not found.")
        return await self._public(document)

    async def create(self, company_id: str, payload: dict[str, Any], actor_id: str) -> dict[str, Any]:
        company = await self._company(company_id)
        role = await self._role(company, payload["role_id"])
        location = await self._location(company, payload.get("parking_location_id"))
        now = datetime.now(UTC)
        user = {
            "company_id": company,
            "email": payload["email"].lower(),
            "username": payload["username"].lower(),
            "password_hash": password_hasher.hash(payload["password"]),
            "display_name": payload["name"],
            "status": "active" if payload["status"] == "active" else "disabled",
            "role_ids": [role["_id"]],
            "is_super_admin": False,
            "created_at": now,
            "updated_at": now,
        }
        try:
            user_result = await self.database.users.insert_one(user)
        except DuplicateKeyError as exc:
            raise ConflictError("Email or username is already in use.") from exc
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
            "salary": Decimal128(str(payload["salary"])),
            "joining_date": self._as_datetime(payload["joining_date"]),
            "parking_location_id": location["_id"] if location else None,
            "status": payload["status"],
            "created_at": now,
            "updated_at": now,
            "created_by": _object_id(actor_id, "Actor"),
            "updated_by": _object_id(actor_id, "Actor"),
        }
        try:
            result = await self.database.employees.insert_one(employee)
        except DuplicateKeyError as exc:
            await self.database.users.delete_one({"_id": user_result.inserted_id})
            raise ConflictError("Employee ID or email already exists in this company.") from exc
        employee["_id"] = result.inserted_id
        return await self._public(employee)

    async def update(self, company_id: str, employee_id: str, payload: dict[str, Any], actor_id: str) -> dict[str, Any]:
        company = await self._company(company_id)
        document = await self.database.employees.find_one({"_id": _object_id(employee_id, "Employee"), "company_id": company, "status": {"$ne": "inactive"}})
        if not document:
            raise NotFoundError("Employee was not found.")
        changes: dict[str, Any] = {"updated_at": datetime.now(UTC), "updated_by": _object_id(actor_id, "Actor")}
        user_changes: dict[str, Any] = {"updated_at": changes["updated_at"]}
        if "role_id" in payload:
            role = await self._role(company, payload["role_id"])
            changes["role_id"] = role["_id"]
            user_changes["role_ids"] = [role["_id"]]
        if "parking_location_id" in payload:
            location = await self._location(company, payload["parking_location_id"])
            changes["parking_location_id"] = location["_id"] if location else None
        for key in ("photo_url", "name", "gender", "phone", "address", "designation", "status"):
            if key in payload:
                changes[key] = payload[key]
        if "salary" in payload:
            changes["salary"] = Decimal128(str(Decimal(payload["salary"])))
        if "joining_date" in payload:
            changes["joining_date"] = self._as_datetime(payload["joining_date"])
        if "employee_id" in payload:
            changes["employee_id"] = payload["employee_id"].upper()
        if "email" in payload:
            changes["email"] = payload["email"].lower()
            user_changes["email"] = changes["email"]
        if "username" in payload:
            changes["username"] = payload["username"].lower()
            user_changes["username"] = changes["username"]
        if "name" in payload:
            user_changes["display_name"] = payload["name"]
        if "status" in payload:
            user_changes["status"] = "active" if payload["status"] == "active" else "disabled"
        if "password" in payload and payload["password"]:
            user_changes["password_hash"] = password_hasher.hash(payload["password"])
        try:
            await self.database.users.update_one({"_id": document["user_id"]}, {"$set": user_changes})
            updated = await self.database.employees.find_one_and_update(
                {"_id": document["_id"]}, {"$set": changes}, return_document=ReturnDocument.AFTER
            )
        except DuplicateKeyError as exc:
            raise ConflictError("Employee ID, email, or username is already in use.") from exc
        if not updated:
            raise NotFoundError("Employee was not found.")
        return await self._public(updated)

    async def deactivate(self, company_id: str, employee_id: str, actor_id: str) -> None:
        company = await self._company(company_id)
        document = await self.database.employees.find_one({"_id": _object_id(employee_id, "Employee"), "company_id": company, "status": {"$ne": "inactive"}})
        if not document:
            raise NotFoundError("Employee was not found.")
        now = datetime.now(UTC)
        await self.database.users.update_one({"_id": document["user_id"]}, {"$set": {"status": "disabled", "updated_at": now}})
        await self.database.employees.update_one(
            {"_id": document["_id"]}, {"$set": {"status": "inactive", "updated_at": now, "updated_by": _object_id(actor_id, "Actor")}}
        )

    async def options(self, company_id: str) -> dict[str, list[dict[str, str]]]:
        company = await self._company(company_id)
        roles = self.database.roles.find({"status": "active", "$or": [{"scope": "system"}, {"scope": "company", "company_id": company}]}).sort("name", 1)
        locations = self.database.parking_locations.find({"company_id": company, "status": "active"}).sort("name", 1)
        return {
            "roles": [{"id": str(item["_id"]), "name": item["name"]} async for item in roles],
            "parking_locations": [{"id": str(item["_id"]), "name": item["name"]} async for item in locations],
        }

    async def export_rows(self, company_id: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        company = await self._company(company_id)
        cursor = self.database.employees.find(self._query(company, filters)).sort("name", 1).limit(10_000)
        return [await self._public(item) async for item in cursor]
