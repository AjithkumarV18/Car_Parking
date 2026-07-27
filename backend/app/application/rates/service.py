from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any

from bson import ObjectId
from bson.decimal128 import Decimal128
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.exceptions import ConflictError, NotFoundError
from app.shared.pagination import Page, PaginationParams


def _object_id(value: str, resource: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise NotFoundError(f"{resource} was not found.")
    return ObjectId(value)


class ParkingRateService:
    """Tenant-scoped CRUD and schedule validation for parking-rate master data."""

    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.database = database

    async def _company(self, company_id: str) -> ObjectId:
        identifier = _object_id(company_id, "Company")
        if not await self.database.companies.find_one({"_id": identifier, "status": "active"}):
            raise NotFoundError("Company was not found or is inactive.")
        return identifier

    @staticmethod
    def _as_datetime(value: date | datetime) -> datetime:
        if isinstance(value, datetime):
            return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
        return datetime.combine(value, time.min, tzinfo=UTC)

    @staticmethod
    def validate_duration_slabs(slabs: list[dict[str, Any]]) -> None:
        """Require a deterministic, contiguous tariff from minute zero onward."""

        if not slabs:
            raise ValueError("At least one duration slab is required.")
        expected_start = 0
        for index, slab in enumerate(slabs):
            start = slab["from_minutes"]
            end = slab.get("to_minutes")
            if start != expected_start:
                raise ValueError("Duration slabs must be contiguous and start at minute 0.")
            if end is None:
                if index != len(slabs) - 1:
                    raise ValueError("Only the final duration slab may have no end time.")
                continue
            if end <= start:
                raise ValueError("A duration slab end must be greater than its start.")
            expected_start = end

    @staticmethod
    def _storage_slabs(slabs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "from_minutes": item["from_minutes"],
                "to_minutes": item.get("to_minutes"),
                "amount": Decimal128(str(Decimal(item["amount"]))),
                "gst_percent": Decimal128(str(Decimal(item["gst_percent"]))),
            }
            for item in slabs
        ]

    def _public(self, document: dict[str, Any]) -> dict[str, Any]:
        effective_date = document["effective_date"]
        return {
            "id": str(document["_id"]),
            "vehicle_type": document["vehicle_type"],
            "duration_slabs": [
                {
                    "from_minutes": slab["from_minutes"],
                    "to_minutes": slab.get("to_minutes"),
                    "amount": str(slab["amount"].to_decimal()),
                    "gst_percent": str(slab["gst_percent"].to_decimal()),
                }
                for slab in document["duration_slabs"]
            ],
            "effective_date": self._as_datetime(effective_date).date().isoformat(),
            "status": document["status"],
        }

    def _query(self, company_id: ObjectId, filters: dict[str, Any]) -> dict[str, Any]:
        query: dict[str, Any] = {"company_id": company_id}
        if filters.get("status"):
            query["status"] = filters["status"]
        else:
            query["status"] = {"$ne": "inactive"}
        if filters.get("vehicle_type"):
            query["vehicle_type"] = filters["vehicle_type"]
        if (search := filters.get("search")) and not filters.get("vehicle_type"):
            normalized = search.strip().lower().replace(" ", "_")
            query["vehicle_type"] = {"$regex": normalized, "$options": "i"}
        effective_date: dict[str, datetime] = {}
        if date_from := filters.get("effective_from"):
            effective_date["$gte"] = self._as_datetime(date_from)
        if date_to := filters.get("effective_to"):
            effective_date["$lte"] = self._as_datetime(date_to)
        if effective_date:
            query["effective_date"] = effective_date
        return query

    async def list(self, company_id: str, pagination: PaginationParams, filters: dict[str, Any]) -> Page[dict[str, Any]]:
        identifier = await self._company(company_id)
        query = self._query(identifier, filters)
        sort_fields = {"vehicle_type", "effective_date", "status", "created_at"}
        sort_by = filters.get("sort_by") if filters.get("sort_by") in sort_fields else "effective_date"
        direction = ASCENDING if filters.get("sort_order") == "asc" else DESCENDING
        total = await self.database.parking_rates.count_documents(query)
        cursor = self.database.parking_rates.find(query).sort(sort_by, direction).skip(pagination.offset).limit(pagination.limit)
        return Page.create(items=[self._public(item) async for item in cursor], total=total, pagination=pagination)

    async def get(self, company_id: str, rate_id: str) -> dict[str, Any]:
        document = await self.database.parking_rates.find_one(
            {"_id": _object_id(rate_id, "Parking rate"), "company_id": await self._company(company_id)}
        )
        if not document:
            raise NotFoundError("Parking rate was not found.")
        return self._public(document)

    async def create(self, company_id: str, payload: dict[str, Any], actor_id: str) -> dict[str, Any]:
        company = await self._company(company_id)
        self.validate_duration_slabs(payload["duration_slabs"])
        now = datetime.now(UTC)
        document = {
            "company_id": company,
            "vehicle_type": payload["vehicle_type"],
            "duration_slabs": self._storage_slabs(payload["duration_slabs"]),
            "effective_date": self._as_datetime(payload["effective_date"]),
            "status": payload["status"],
            "created_at": now,
            "updated_at": now,
            "created_by": _object_id(actor_id, "Actor"),
            "updated_by": _object_id(actor_id, "Actor"),
        }
        try:
            result = await self.database.parking_rates.insert_one(document)
        except DuplicateKeyError as exc:
            raise ConflictError("A parking rate already exists for this vehicle type and effective date.") from exc
        document["_id"] = result.inserted_id
        return self._public(document)

    async def update(self, company_id: str, rate_id: str, payload: dict[str, Any], actor_id: str) -> dict[str, Any]:
        company = await self._company(company_id)
        current = await self.database.parking_rates.find_one({"_id": _object_id(rate_id, "Parking rate"), "company_id": company})
        if not current:
            raise NotFoundError("Parking rate was not found.")
        if "duration_slabs" in payload:
            self.validate_duration_slabs(payload["duration_slabs"])
        changes: dict[str, Any] = {
            "updated_at": datetime.now(UTC),
            "updated_by": _object_id(actor_id, "Actor"),
        }
        for key in ("vehicle_type", "status"):
            if key in payload:
                changes[key] = payload[key]
        if "duration_slabs" in payload:
            changes["duration_slabs"] = self._storage_slabs(payload["duration_slabs"])
        if "effective_date" in payload:
            changes["effective_date"] = self._as_datetime(payload["effective_date"])
        try:
            updated = await self.database.parking_rates.find_one_and_update(
                {"_id": current["_id"]}, {"$set": changes}, return_document=ReturnDocument.AFTER
            )
        except DuplicateKeyError as exc:
            raise ConflictError("A parking rate already exists for this vehicle type and effective date.") from exc
        if not updated:
            raise NotFoundError("Parking rate was not found.")
        return self._public(updated)

    async def deactivate(self, company_id: str, rate_id: str, actor_id: str) -> None:
        company = await self._company(company_id)
        result = await self.database.parking_rates.update_one(
            {"_id": _object_id(rate_id, "Parking rate"), "company_id": company, "status": {"$ne": "inactive"}},
            {"$set": {"status": "inactive", "updated_at": datetime.now(UTC), "updated_by": _object_id(actor_id, "Actor")}},
        )
        if result.matched_count == 0:
            raise NotFoundError("Parking rate was not found.")
