from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Any

from bson import ObjectId
from bson.decimal128 import Decimal128
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.exceptions import ConflictError, NotFoundError


def _id(value: str, name: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise NotFoundError(f"{name} was not found.")
    return ObjectId(value)


def _public(document: dict[str, Any]) -> dict[str, Any]:
    result = {**document, "id": str(document["_id"])}
    for key in ("company_id", "parking_location_id", "parking_slot_id", "created_by", "updated_by"):
        if result.get(key) is not None:
            result[key] = str(result[key])
    for key, value in list(result.items()):
        if isinstance(value, Decimal128):
            result[key] = f"{value.to_decimal():.2f}"
    result.pop("_id", None)
    return result


class AdvancedParkingService:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.database = database

    async def _company(self, company_id: str) -> ObjectId:
        identifier = _id(company_id, "Company")
        company = await self.database.companies.find_one({"_id": identifier, "status": "active"})
        if not company:
            raise NotFoundError("Company was not found or is inactive.")
        return identifier

    @staticmethod
    def _as_datetime(value: date | datetime) -> datetime:
        if isinstance(value, datetime):
            return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
        return datetime.combine(value, time.min, tzinfo=UTC)

    async def locations(self, company_id: str) -> list[dict[str, str | None]]:
        company = await self._company(company_id)
        branches = {
            branch["_id"]: branch.get("name")
            async for branch in self.database.branches.find({"company_id": company, "status": "active"})
        }
        return [
            {"id": str(location["_id"]), "name": location["name"], "branch_name": branches.get(location.get("branch_id"))}
            async for location in self.database.parking_locations.find({"company_id": company, "status": "active"}).sort("name", ASCENDING)
        ]

    async def passes(self, company_id: str) -> list[dict[str, Any]]:
        company = await self._company(company_id)
        cursor = self.database.monthly_passes.find({"company_id": company}).sort("valid_until", ASCENDING)
        return [_public(item) async for item in cursor]

    async def create_pass(self, company_id: str, payload: dict[str, Any], actor_id: str) -> dict[str, Any]:
        company = await self._company(company_id)
        now = datetime.now(UTC)
        location_id = payload.get("parking_location_id")
        if location_id:
            await self._location(company, location_id)
            payload["parking_location_id"] = _id(location_id, "Parking location")
        sequence = await self.database.parking_counters.find_one_and_update(
            {"key": f"monthly_pass:{company}:{now:%Y%m}"},
            {"$inc": {"sequence": 1}, "$set": {"company_id": company, "updated_at": now}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        document = {
            **payload,
            "company_id": company,
            "pass_number": f"MP-{now:%Y%m}-{sequence['sequence']:05d}",
            "amount": Decimal128(str(payload["amount"])),
            "created_at": now,
            "created_by": _id(actor_id, "Actor"),
        }
        document["valid_from"] = self._as_datetime(payload["valid_from"])
        document["valid_until"] = self._as_datetime(payload["valid_until"])
        result = await self.database.monthly_passes.insert_one(document)
        document["_id"] = result.inserted_id
        return _public(document)

    async def update_pass(self, company_id: str, pass_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        company = await self._company(company_id)
        if not payload:
            raise ConflictError("Provide at least one value to update.")
        current = await self.database.monthly_passes.find_one({"_id": _id(pass_id, "Monthly pass"), "company_id": company})
        if not current:
            raise NotFoundError("Monthly pass was not found.")
        if "amount" in payload:
            payload["amount"] = Decimal128(str(payload["amount"]))
        if "valid_until" in payload:
            payload["valid_until"] = self._as_datetime(payload["valid_until"])
            if payload["valid_until"] < current["valid_from"]:
                raise ConflictError("Pass end date must not be before its start date.")
        updated = await self.database.monthly_passes.find_one_and_update(
            {"_id": _id(pass_id, "Monthly pass"), "company_id": company},
            {"$set": payload},
            return_document=ReturnDocument.AFTER,
        )
        if not updated:
            raise NotFoundError("Monthly pass was not found.")
        return _public(updated)

    async def slots(self, company_id: str, location_id: str | None = None) -> list[dict[str, Any]]:
        company = await self._company(company_id)
        query: dict[str, Any] = {"company_id": company}
        if location_id:
            await self._location(company, location_id)
            query["parking_location_id"] = _id(location_id, "Parking location")
        now = datetime.now(UTC)
        reservations = {
            item["parking_slot_id"]: item
            async for item in self.database.reserved_slots.find(
                {"company_id": company, "status": "active", "valid_from": {"$lte": now}, "valid_until": {"$gt": now}}
            )
        }
        result: list[dict[str, Any]] = []
        async for slot in self.database.parking_slots.find(query).sort("slot_number", ASCENDING):
            public = _public(slot)
            if slot.get("status") == "occupied":
                public["occupied_by"] = slot.get("occupied_by")
            elif reservation := reservations.get(slot["_id"]):
                public["status"] = "reserved"
                public["reserved_for"] = reservation["holder_name"]
            elif slot.get("status") == "reserved":
                # Reservations are time-bound. A stale reservation must not make a slot appear unavailable.
                public["status"] = "available"
            result.append(public)
        return result

    async def create_slot(self, company_id: str, payload: dict[str, Any], actor_id: str) -> dict[str, Any]:
        company = await self._company(company_id)
        location = await self._location(company, payload.pop("parking_location_id"))
        document = {
            **payload,
            "company_id": company,
            "parking_location_id": location,
            "created_by": _id(actor_id, "Actor"),
        }
        try:
            result = await self.database.parking_slots.insert_one(document)
        except DuplicateKeyError as exc:
            raise ConflictError("A slot with this number already exists at this location.") from exc
        document["_id"] = result.inserted_id
        return _public(document)

    async def update_slot(self, company_id: str, slot_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        company = await self._company(company_id)
        if not payload:
            raise ConflictError("Provide at least one value to update.")
        updated = await self.database.parking_slots.find_one_and_update(
            {"_id": _id(slot_id, "Parking slot"), "company_id": company},
            {"$set": payload},
            return_document=ReturnDocument.AFTER,
        )
        if not updated:
            raise NotFoundError("Parking slot was not found.")
        return _public(updated)

    async def reservations(self, company_id: str) -> list[dict[str, Any]]:
        company = await self._company(company_id)
        slots = {
            slot["_id"]: slot["slot_number"]
            async for slot in self.database.parking_slots.find({"company_id": company})
        }
        cursor = self.database.reserved_slots.find({"company_id": company}).sort("valid_until", ASCENDING)
        now = datetime.now(UTC)
        reservations: list[dict[str, Any]] = []
        async for item in cursor:
            reservation = {**_public(item), "slot_number": slots.get(item["parking_slot_id"])}
            if reservation["status"] == "active" and self._as_datetime(reservation["valid_until"]) <= now:
                reservation["status"] = "expired"
            reservations.append(reservation)
        return reservations

    async def create_reservation(self, company_id: str, payload: dict[str, Any], actor_id: str) -> dict[str, Any]:
        company = await self._company(company_id)
        slot = _id(payload.pop("parking_slot_id"), "Parking slot")
        payload["valid_from"] = self._as_datetime(payload["valid_from"])
        payload["valid_until"] = self._as_datetime(payload["valid_until"])
        slot_document = await self.database.parking_slots.find_one({"_id": slot, "company_id": company})
        if not slot_document:
            raise NotFoundError("Parking slot was not found.")
        if slot_document.get("status") in {"occupied", "maintenance"}:
            raise ConflictError("The selected slot is not available for reservation.")
        overlap = await self.database.reserved_slots.find_one(
            {
                "company_id": company,
                "parking_slot_id": slot,
                "status": "active",
                "valid_until": {"$gt": payload["valid_from"]},
                "valid_from": {"$lt": payload["valid_until"]},
            }
        )
        if overlap:
            raise ConflictError("The selected slot already has an overlapping reservation.")
        document = {
            **payload,
            "company_id": company,
            "parking_slot_id": slot,
            "created_at": datetime.now(UTC),
            "created_by": _id(actor_id, "Actor"),
        }
        result = await self.database.reserved_slots.insert_one(document)
        document["_id"] = result.inserted_id
        await self._sync_slot_reservation_status(company, slot)
        return {**_public(document), "slot_number": slot_document["slot_number"]}

    async def update_reservation(self, company_id: str, reservation_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        company = await self._company(company_id)
        if not payload:
            raise ConflictError("Provide at least one value to update.")
        identifier = _id(reservation_id, "Reserved slot")
        current = await self.database.reserved_slots.find_one({"_id": identifier, "company_id": company})
        if not current:
            raise NotFoundError("Reserved slot was not found.")
        if "valid_from" in payload:
            payload["valid_from"] = self._as_datetime(payload["valid_from"])
        if "valid_until" in payload:
            payload["valid_until"] = self._as_datetime(payload["valid_until"])
        valid_from = payload.get("valid_from", self._as_datetime(current["valid_from"]))
        valid_until = payload.get("valid_until", self._as_datetime(current["valid_until"]))
        status = payload.get("status", current["status"])
        if valid_until <= valid_from:
            raise ConflictError("Reservation end must be after its start.")
        if status == "active":
            overlap = await self.database.reserved_slots.find_one(
                {
                    "_id": {"$ne": identifier}, "company_id": company, "parking_slot_id": current["parking_slot_id"],
                    "status": "active", "valid_until": {"$gt": valid_from}, "valid_from": {"$lt": valid_until},
                }
            )
            if overlap:
                raise ConflictError("The selected slot already has an overlapping reservation.")
        updated = await self.database.reserved_slots.find_one_and_update(
            {"_id": identifier, "company_id": company},
            {"$set": payload},
            return_document=ReturnDocument.AFTER,
        )
        if not updated:
            raise NotFoundError("Reserved slot was not found.")
        await self._sync_slot_reservation_status(company, updated["parking_slot_id"])
        slot = await self.database.parking_slots.find_one({"_id": updated["parking_slot_id"], "company_id": company})
        return {**_public(updated), "slot_number": slot.get("slot_number") if slot else None}

    async def _sync_slot_reservation_status(self, company: ObjectId, slot_id: ObjectId) -> None:
        """Reflect a currently active reservation without blocking future reservations early."""

        slot = await self.database.parking_slots.find_one({"_id": slot_id, "company_id": company})
        if not slot or slot.get("status") in {"occupied", "maintenance"}:
            return
        now = datetime.now(UTC)
        reservation = await self.database.reserved_slots.find_one(
            {
                "company_id": company,
                "parking_slot_id": slot_id,
                "status": "active",
                "valid_from": {"$lte": now},
                "valid_until": {"$gt": now},
            }
        )
        await self.database.parking_slots.update_one(
            {"_id": slot_id, "company_id": company, "status": {"$nin": ["occupied", "maintenance"]}},
            {"$set": {"status": "reserved" if reservation else "available", "updated_at": now}},
        )

    async def _location(self, company: ObjectId, location_id: str) -> ObjectId:
        location = _id(location_id, "Parking location")
        exists = await self.database.parking_locations.find_one(
            {"_id": location, "company_id": company, "status": "active"}
        )
        if not exists:
            raise NotFoundError("Parking location was not found.")
        return location
