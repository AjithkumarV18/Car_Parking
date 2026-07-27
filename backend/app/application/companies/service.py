from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.exceptions import ConflictError, NotFoundError
from app.shared.pagination import Page, PaginationParams


def _object_id(value: str, resource: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise NotFoundError(f"{resource} was not found.")
    return ObjectId(value)


def _public(document: dict[str, Any]) -> dict[str, Any]:
    document = {**document}
    document["id"] = str(document.pop("_id"))
    for key in ("company_id", "branch_id", "created_by", "updated_by"):
        if document.get(key) is not None:
            document[key] = str(document[key])
    return document


def _code_from_name(name: str) -> str:
    code = re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")
    return code[:40] or "COMPANY"


class CompanyService:
    """Master-data service for platform-managed companies and facilities."""

    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.database = database

    async def list_companies(self, pagination: PaginationParams) -> Page[dict[str, Any]]:
        query: dict[str, Any] = {"status": {"$ne": "inactive"}}
        total = await self.database.companies.count_documents(query)
        cursor = (
            self.database.companies.find(query)
            .sort("company_name", 1)
            .skip(pagination.offset)
            .limit(pagination.limit)
        )
        items = [_public(document) async for document in cursor]
        return Page.create(items=items, total=total, pagination=pagination)

    async def get_company(self, company_id: str) -> dict[str, Any]:
        company = await self.database.companies.find_one(
            {"_id": _object_id(company_id, "Company"), "status": {"$ne": "inactive"}}
        )
        if not company:
            raise NotFoundError("Company was not found.")
        return _public(company)

    async def create_company(self, payload: dict[str, Any], actor_id: str) -> dict[str, Any]:
        del payload, actor_id
        raise ConflictError("Companies can only be created during the initial application setup.")

    async def update_company(self, company_id: str, payload: dict[str, Any], actor_id: str) -> dict[str, Any]:
        identifier = _object_id(company_id, "Company")
        changes = {**payload, "updated_at": datetime.now(UTC), "updated_by": ObjectId(actor_id)}
        try:
            updated = await self.database.companies.find_one_and_update(
                {"_id": identifier, "status": {"$ne": "inactive"}},
                {"$set": changes},
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError as exc:
            raise ConflictError("A company with this code already exists.") from exc
        if not updated:
            raise NotFoundError("Company was not found.")
        return _public(updated)

    async def deactivate_company(self, company_id: str, actor_id: str) -> None:
        del company_id, actor_id
        raise ConflictError("Company deactivation is disabled. Manage branches and parking locations instead.")

    async def _company_active(self, company_id: str) -> ObjectId:
        identifier = _object_id(company_id, "Company")
        if not await self.database.companies.find_one({"_id": identifier, "status": "active"}):
            raise NotFoundError("Company was not found or is inactive.")
        return identifier

    async def list_branches(self, company_id: str, pagination: PaginationParams) -> Page[dict[str, Any]]:
        identifier = await self._company_active(company_id)
        query = {"company_id": identifier, "status": {"$ne": "inactive"}}
        total = await self.database.branches.count_documents(query)
        cursor = self.database.branches.find(query).sort("name", 1).skip(pagination.offset).limit(pagination.limit)
        return Page.create(
            items=[_public(document) async for document in cursor], total=total, pagination=pagination
        )

    async def create_branch(self, company_id: str, payload: dict[str, Any], actor_id: str) -> dict[str, Any]:
        identifier = await self._company_active(company_id)
        now = datetime.now(UTC)
        document = {
            **payload,
            "company_id": identifier,
            "code": payload.get("code") or _code_from_name(payload["name"]),
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "created_by": ObjectId(actor_id),
            "updated_by": ObjectId(actor_id),
        }
        try:
            result = await self.database.branches.insert_one(document)
        except DuplicateKeyError as exc:
            raise ConflictError("A branch with this code already exists in this company.") from exc
        document["_id"] = result.inserted_id
        return _public(document)

    async def update_branch(
        self,
        company_id: str,
        branch_id: str,
        payload: dict[str, Any],
        actor_id: str,
    ) -> dict[str, Any]:
        identifier = await self._company_active(company_id)
        updated = await self.database.branches.find_one_and_update(
            {"_id": _object_id(branch_id, "Branch"), "company_id": identifier, "status": {"$ne": "inactive"}},
            {"$set": {**payload, "updated_at": datetime.now(UTC), "updated_by": ObjectId(actor_id)}},
            return_document=ReturnDocument.AFTER,
        )
        if not updated:
            raise NotFoundError("Branch was not found.")
        return _public(updated)

    async def deactivate_branch(self, company_id: str, branch_id: str, actor_id: str) -> None:
        identifier = await self._company_active(company_id)
        branch = _object_id(branch_id, "Branch")
        now = datetime.now(UTC)
        result = await self.database.branches.update_one(
            {"_id": branch, "company_id": identifier, "status": {"$ne": "inactive"}},
            {"$set": {"status": "inactive", "updated_at": now, "updated_by": ObjectId(actor_id)}},
        )
        if result.modified_count != 1:
            raise NotFoundError("Branch was not found.")
        await self.database.parking_locations.update_many(
            {"company_id": identifier, "branch_id": branch, "status": {"$ne": "inactive"}},
            {"$set": {"status": "inactive", "updated_at": now}},
        )

    async def _branch_active(self, company_id: str, branch_id: str) -> tuple[ObjectId, ObjectId]:
        company = await self._company_active(company_id)
        branch = _object_id(branch_id, "Branch")
        if not await self.database.branches.find_one({"_id": branch, "company_id": company, "status": "active"}):
            raise NotFoundError("Branch was not found or is inactive.")
        return company, branch

    async def list_locations(
        self, company_id: str, branch_id: str, pagination: PaginationParams
    ) -> Page[dict[str, Any]]:
        company, branch = await self._branch_active(company_id, branch_id)
        query = {"company_id": company, "branch_id": branch, "status": {"$ne": "inactive"}}
        total = await self.database.parking_locations.count_documents(query)
        cursor = (
            self.database.parking_locations.find(query)
            .sort("name", 1)
            .skip(pagination.offset)
            .limit(pagination.limit)
        )
        return Page.create(
            items=[_public(document) async for document in cursor], total=total, pagination=pagination
        )

    async def create_location(
        self, company_id: str, branch_id: str, payload: dict[str, Any], actor_id: str
    ) -> dict[str, Any]:
        company, branch = await self._branch_active(company_id, branch_id)
        now = datetime.now(UTC)
        document = {
            **payload,
            "company_id": company,
            "branch_id": branch,
            "code": payload.get("code") or _code_from_name(payload["name"]),
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "created_by": ObjectId(actor_id),
            "updated_by": ObjectId(actor_id),
        }
        try:
            result = await self.database.parking_locations.insert_one(document)
        except DuplicateKeyError as exc:
            raise ConflictError("A parking location with this code already exists in this branch.") from exc
        document["_id"] = result.inserted_id
        return _public(document)

    async def update_location(
        self, company_id: str, branch_id: str, location_id: str, payload: dict[str, Any], actor_id: str
    ) -> dict[str, Any]:
        company, branch = await self._branch_active(company_id, branch_id)
        updated = await self.database.parking_locations.find_one_and_update(
            {
                "_id": _object_id(location_id, "Parking location"),
                "company_id": company,
                "branch_id": branch,
                "status": {"$ne": "inactive"},
            },
            {"$set": {**payload, "updated_at": datetime.now(UTC), "updated_by": ObjectId(actor_id)}},
            return_document=ReturnDocument.AFTER,
        )
        if not updated:
            raise NotFoundError("Parking location was not found.")
        return _public(updated)

    async def deactivate_location(self, company_id: str, branch_id: str, location_id: str, actor_id: str) -> None:
        company, branch = await self._branch_active(company_id, branch_id)
        result = await self.database.parking_locations.update_one(
            {
                "_id": _object_id(location_id, "Parking location"),
                "company_id": company,
                "branch_id": branch,
                "status": {"$ne": "inactive"},
            },
            {"$set": {"status": "inactive", "updated_at": datetime.now(UTC), "updated_by": ObjectId(actor_id)}},
        )
        if result.modified_count != 1:
            raise NotFoundError("Parking location was not found.")
