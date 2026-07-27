from __future__ import annotations

import asyncio
import base64
import logging
import math
import re
from datetime import UTC, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from bson import ObjectId
from bson.decimal128 import Decimal128
from gridfs.errors import NoFile
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from pymongo import DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.core.exceptions import ConflictError, DatabaseUnavailableError, InvalidReceiptIdError, NotFoundError
from app.core.software_settings import SOFTWARE_FEATURE_DEFAULTS
from app.shared.pagination import Page, PaginationParams

MONEY_QUANTUM = Decimal("0.01")
logger = logging.getLogger(__name__)


def _object_id(value: str, resource: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise NotFoundError(f"{resource} was not found.")
    return ObjectId(value)


def _receipt_object_id(value: str, receipt_type: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise InvalidReceiptIdError(f"{receipt_type} receipt ID must be a valid 24-character identifier.")
    return ObjectId(value)


def _decimal(value: Any) -> Decimal:
    return value.to_decimal() if isinstance(value, Decimal128) else Decimal(str(value))


def _money(value: Any) -> Decimal:
    return _decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _money_string(value: Any) -> str:
    return f"{_money(value):.2f}"


def _utc_datetime(value: datetime) -> datetime:
    """Normalize MongoDB legacy timestamps and new UTC values before arithmetic."""

    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class ParkingOperationsService:
    """Tenant-safe vehicle entry, tariff settlement, payment, and receipt operations."""

    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.database = database

    async def _company(self, company_id: str) -> dict[str, Any]:
        company = await self.database.companies.find_one({"_id": _object_id(company_id, "Company"), "status": "active"})
        if not company:
            raise NotFoundError("Company was not found or is inactive.")
        return company

    async def _operator_location(self, company_id: ObjectId, actor_id: str) -> tuple[ObjectId | None, str | None]:
        employee = await self.database.employees.find_one(
            {"company_id": company_id, "user_id": _object_id(actor_id, "Actor"), "status": "active"}
        )
        location_id = employee.get("parking_location_id") if employee else None
        if not location_id:
            return None, None
        location = await self.database.parking_locations.find_one(
            {"_id": location_id, "company_id": company_id, "status": "active"}
        )
        return (location["_id"], location["name"]) if location else (None, None)

    async def _claim_active_reservation(
        self,
        company_id: ObjectId,
        vehicle_number: str,
        operator_location_id: ObjectId | None,
        entry_id: ObjectId,
        now: datetime,
    ) -> tuple[ObjectId | None, ObjectId | None, ObjectId | None]:
        """Atomically occupy the current reservation matching a vehicle entry."""

        reservation = await self.database.reserved_slots.find_one(
            {
                "company_id": company_id,
                "vehicle_number": vehicle_number,
                "status": "active",
                "valid_from": {"$lte": now},
                "valid_until": {"$gt": now},
            },
            sort=[("valid_from", DESCENDING)],
        )
        if not reservation:
            return None, None, None
        slot = await self.database.parking_slots.find_one(
            {"_id": reservation["parking_slot_id"], "company_id": company_id}
        )
        if not slot:
            raise ConflictError("The parking slot assigned to this reservation is unavailable.")
        if operator_location_id and slot["parking_location_id"] != operator_location_id:
            raise ConflictError("This vehicle is reserved for a different parking location.")
        claimed_slot = await self.database.parking_slots.find_one_and_update(
            {
                "_id": slot["_id"],
                "company_id": company_id,
                "status": {"$in": ["available", "reserved"]},
            },
            {
                "$set": {
                    "status": "occupied",
                    "occupied_by": vehicle_number,
                    "occupied_entry_id": entry_id,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if not claimed_slot:
            raise ConflictError("The reserved parking slot is not currently available.")
        claimed_reservation = await self.database.reserved_slots.find_one_and_update(
            {
                "_id": reservation["_id"],
                "company_id": company_id,
                "status": "active",
                "valid_from": {"$lte": now},
                "valid_until": {"$gt": now},
            },
            {"$set": {"claimed_entry_id": entry_id, "claimed_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        if not claimed_reservation:
            await self.database.parking_slots.update_one(
                {"_id": slot["_id"], "company_id": company_id, "occupied_entry_id": entry_id},
                {"$set": {"status": "available", "updated_at": now}, "$unset": {"occupied_by": "", "occupied_entry_id": ""}},
            )
            raise ConflictError("The slot reservation is no longer active.")
        return slot["_id"], reservation["_id"], slot["parking_location_id"]

    async def _release_reservation_claim(
        self,
        company_id: ObjectId,
        slot_id: ObjectId | None,
        reservation_id: ObjectId | None,
        entry_id: ObjectId,
        now: datetime,
    ) -> None:
        """Undo a provisional reservation claim when a vehicle entry cannot be saved."""

        if reservation_id:
            await self.database.reserved_slots.update_one(
                {"_id": reservation_id, "company_id": company_id, "claimed_entry_id": entry_id},
                {"$unset": {"claimed_entry_id": "", "claimed_at": ""}},
            )
        if slot_id:
            await self.database.parking_slots.update_one(
                {"_id": slot_id, "company_id": company_id, "status": "occupied", "occupied_entry_id": entry_id},
                {"$set": {"status": "reserved", "updated_at": now}, "$unset": {"occupied_by": "", "occupied_entry_id": ""}},
            )

    async def _complete_reservation_on_exit(
        self,
        company_id: ObjectId,
        entry: dict[str, Any],
        exit_id: ObjectId,
        now: datetime,
    ) -> None:
        """Complete the reservation consumed by an entry and make its slot available."""

        slot_id = entry.get("parking_slot_id")
        reservation_id = entry.get("reservation_id")
        if not slot_id or not reservation_id:
            return
        await self.database.reserved_slots.update_one(
            {
                "_id": reservation_id,
                "company_id": company_id,
                "status": "active",
                "claimed_entry_id": entry["_id"],
            },
            {"$set": {"status": "completed", "completed_at": now, "exit_id": exit_id}},
        )
        await self.database.parking_slots.update_one(
            {"_id": slot_id, "company_id": company_id, "status": "occupied", "occupied_entry_id": entry["_id"]},
            {"$set": {"status": "available", "updated_at": now}, "$unset": {"occupied_by": "", "occupied_entry_id": ""}},
        )

    async def _software_settings(self, company_id: ObjectId) -> dict[str, bool]:
        document = await self.database.software_settings.find_one({"company_id": company_id})
        return {key: bool((document or {}).get(key, default)) for key, default in SOFTWARE_FEATURE_DEFAULTS.items()}

    async def _active_rate(self, company_id: ObjectId, vehicle_type: str, at: datetime) -> dict[str, Any]:
        rate = await self.database.parking_rates.find_one(
            {"company_id": company_id, "vehicle_type": vehicle_type, "status": "active", "effective_date": {"$lte": at}},
            sort=[("effective_date", DESCENDING)],
        )
        if not rate:
            raise NotFoundError("No active parking rate is configured for this vehicle type.")
        return rate

    async def _next_sequence(self, company_id: ObjectId, at: datetime) -> int:
        day = at.strftime("%Y%m%d")
        counter = await self.database.parking_counters.find_one_and_update(
            {"key": f"entry:{company_id}:{day}"},
            {
                "$inc": {"sequence": 1},
                "$set": {"company_id": company_id, "updated_at": at},
                "$setOnInsert": {"key": f"entry:{company_id}:{day}", "created_at": at},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return int(counter["sequence"])

    async def _save_image(self, company_id: ObjectId, vehicle_number: str, image_data: str | None) -> ObjectId | None:
        if not image_data:
            return None
        header, encoded = image_data.split(",", maxsplit=1)
        content_type = header[5:].split(";", maxsplit=1)[0].lower()
        raw = base64.b64decode(encoded)
        suffix = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[content_type]
        bucket = AsyncIOMotorGridFSBucket(self.database, bucket_name="vehicle_images")
        return await bucket.upload_from_stream(
            f"{vehicle_number}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}.{suffix}",
            raw,
            metadata={"company_id": company_id, "content_type": content_type},
        )

    async def _public_entry(self, document: dict[str, Any]) -> dict[str, Any]:
        location_name = None
        if location_id := document.get("location_id"):
            location = await self.database.parking_locations.find_one({"_id": location_id, "company_id": document["company_id"]})
            location_name = location["name"] if location else None
        return {
            "id": str(document["_id"]),
            "vehicle_number": document["vehicle_number"],
            "rfid": document.get("rfid"),
            "qr_code": document.get("qr_code"),
            "vehicle_type": document["vehicle_type"],
            "entry_at": document["entry_at"],
            "parking_number": document["parking_number"],
            "token_number": document["token_number"],
            "owner_name": document.get("owner_name"),
            "mobile": document.get("mobile"),
            "vehicle_image_available": bool(document.get("vehicle_image_file_id")),
            "advance_amount": _money_string(document["advance_amount"]),
            "location_name": location_name,
            "operator": await self._receipt_operator(document["company_id"], document.get("entry_by")),
            "status": document["status"],
        }

    async def create_entry(self, company_id: str, payload: dict[str, Any], actor_id: str) -> dict[str, Any]:
        company = await self._company(company_id)
        features = await self._software_settings(company["_id"])
        if payload.get("rfid") and not features["rfid_entry_enabled"]:
            raise ConflictError("RFID entry is disabled in software settings.")
        if payload.get("qr_code") and not features["qr_entry_enabled"]:
            raise ConflictError("QR entry is disabled in software settings.")
        if payload.get("vehicle_image_data") and not features["vehicle_image_capture_enabled"]:
            raise ConflictError("Vehicle image capture is disabled in software settings.")
        if payload.get("advance_amount", Decimal("0.00")) > 0 and not features["advance_payment_enabled"]:
            raise ConflictError("Advance payment is disabled in software settings.")
        now = datetime.now(UTC)
        identifiers: list[dict[str, str]] = [{"vehicle_number": payload["vehicle_number"]}]
        if payload.get("rfid"):
            identifiers.append({"rfid": payload["rfid"]})
        if payload.get("qr_code"):
            identifiers.append({"qr_code": payload["qr_code"]})
        if await self.database.vehicle_entries.find_one({"company_id": company["_id"], "status": "open", "$or": identifiers}):
            raise ConflictError("This vehicle, RFID, or QR code already has an open parking entry.")
        rate = await self._active_rate(company["_id"], payload["vehicle_type"], now)
        sequence = await self._next_sequence(company["_id"], now)
        day = now.strftime("%Y%m%d")
        location_id, _ = await self._operator_location(company["_id"], actor_id)
        entry_id = ObjectId()
        slot_id, reservation_id, reservation_location_id = await self._claim_active_reservation(
            company["_id"], payload["vehicle_number"], location_id, entry_id, now
        )
        if reservation_location_id:
            location_id = reservation_location_id
        try:
            image_file_id = await self._save_image(company["_id"], payload["vehicle_number"], payload.get("vehicle_image_data"))
        except Exception:
            await self._release_reservation_claim(company["_id"], slot_id, reservation_id, entry_id, now)
            raise
        document = {
            "_id": entry_id,
            "company_id": company["_id"],
            "location_id": location_id,
            **({"parking_slot_id": slot_id, "reservation_id": reservation_id} if slot_id and reservation_id else {}),
            "vehicle_number": payload["vehicle_number"],
            "rfid": payload.get("rfid"),
            "qr_code": payload.get("qr_code"),
            "vehicle_type": payload["vehicle_type"],
            "entry_at": now,
            "parking_number": f"P-{day}-{sequence:05d}",
            "token_number": f"T-{day}-{sequence:05d}",
            "owner_name": payload.get("owner_name"),
            "mobile": payload.get("mobile"),
            "vehicle_image_file_id": image_file_id,
            "advance_amount": Decimal128(str(_money(payload["advance_amount"]))),
            "rate_snapshot": {
                "rate_id": rate["_id"],
                "effective_date": rate["effective_date"],
                "duration_slabs": rate["duration_slabs"],
            },
            "entry_by": _object_id(actor_id, "Actor"),
            "status": "open",
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = await self.database.vehicle_entries.insert_one(document)
        except DuplicateKeyError as exc:
            await self._release_reservation_claim(company["_id"], slot_id, reservation_id, entry_id, now)
            if image_file_id:
                await AsyncIOMotorGridFSBucket(self.database, bucket_name="vehicle_images").delete(image_file_id)
            raise ConflictError("A matching active vehicle entry already exists.") from exc
        document["_id"] = result.inserted_id
        return await self._public_entry(document)

    async def get_entry(self, company_id: str, entry_id: str) -> dict[str, Any]:
        company = await self._company(company_id)
        entry = await self.database.vehicle_entries.find_one({"_id": _object_id(entry_id, "Vehicle entry"), "company_id": company["_id"]})
        if not entry:
            raise NotFoundError("Vehicle entry was not found.")
        return await self._public_entry(entry)

    async def entry_log(self, company_id: str, pagination: PaginationParams, search: str | None = None) -> Page[dict[str, Any]]:
        company = await self._company(company_id)
        query: dict[str, Any] = {"company_id": company["_id"], "status": "open"}
        if search and (normalized := self._normalized_vehicle_number(search)):
            pattern = {"$regex": normalized, "$options": "i"}
            query["$or"] = [{"vehicle_number": pattern}, {"token_number": pattern}, {"parking_number": pattern}]
        total = await self.database.vehicle_entries.count_documents(query)
        cursor = self.database.vehicle_entries.find(query).sort("entry_at", DESCENDING).skip(pagination.offset).limit(pagination.limit)
        return Page.create(items=[await self._public_entry(entry) async for entry in cursor], total=total, pagination=pagination)

    @staticmethod
    def _normalized_vehicle_number(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9]", "", value).upper()

    async def lookup_open_entry(self, company_id: str, identifiers: dict[str, str | None]) -> dict[str, Any]:
        company = await self._company(company_id)
        features = await self._software_settings(company["_id"])
        if identifiers.get("qr_code") and not features["qr_exit_enabled"]:
            raise ConflictError("QR exit lookup is disabled in software settings.")
        if identifiers.get("rfid") and not features["rfid_exit_enabled"]:
            raise ConflictError("RFID exit lookup is disabled in software settings.")
        matches: list[dict[str, str]] = []
        if vehicle_number := identifiers.get("vehicle_number"):
            matches.append({"vehicle_number": self._normalized_vehicle_number(vehicle_number)})
        if card := identifiers.get("card"):
            matches.append({"token_number": card.strip().upper()})
        if qr_code := identifiers.get("qr_code"):
            matches.append({"qr_code": qr_code.strip()})
        if rfid := identifiers.get("rfid"):
            matches.append({"rfid": rfid.strip()})
        entry = await self.database.vehicle_entries.find_one({"company_id": company["_id"], "status": "open", "$or": matches})
        if not entry:
            raise NotFoundError("No open vehicle entry matches the supplied identifier.")
        return await self._public_entry(entry)

    async def recent_open_entries(self, company_id: str, search: str | None = None, limit: int = 8) -> list[dict[str, Any]]:
        """Return a small, tenant-safe recovery list for the exit operator screen."""

        company = await self._company(company_id)
        query: dict[str, Any] = {"company_id": company["_id"], "status": "open"}
        if search and (normalized := self._normalized_vehicle_number(search)):
            query["vehicle_number"] = {"$regex": normalized, "$options": "i"}
        cursor = self.database.vehicle_entries.find(query).sort("entry_at", DESCENDING).limit(limit)
        return [
            {
                "id": str(entry["_id"]),
                "vehicle_number": entry["vehicle_number"],
                "token_number": entry["token_number"],
                "parking_number": entry["parking_number"],
                "vehicle_type": entry["vehicle_type"],
                "entry_at": entry["entry_at"],
            }
            async for entry in cursor
        ]

    async def active_membership(self, company_id: str, vehicle_number: str) -> dict[str, Any]:
        """Return the currently-valid monthly pass for a vehicle, if one exists."""

        company = await self._company(company_id)
        normalized = self._normalized_vehicle_number(vehicle_number)
        now = datetime.now(UTC)
        today_start = datetime.combine(now.date(), time.min, tzinfo=UTC)
        monthly_pass = await self.database.monthly_passes.find_one(
            {
                "company_id": company["_id"],
                "vehicle_number": normalized,
                "status": "active",
                "valid_from": {"$lte": now},
                "valid_until": {"$gte": today_start},
            },
            sort=[("valid_until", DESCENDING)],
        )
        if not monthly_pass:
            return {"vehicle_number": normalized, "has_active_pass": False}

        valid_until = _utc_datetime(monthly_pass["valid_until"])
        remaining_days = max(0, (valid_until.date() - now.date()).days + 1)
        return {
            "vehicle_number": normalized,
            "has_active_pass": True,
            "pass_number": monthly_pass["pass_number"],
            "holder_name": monthly_pass["holder_name"],
            "valid_until": valid_until,
            "remaining_days": remaining_days,
            "amount": _money_string(monthly_pass["amount"]),
        }

    def _calculation_for_entry(self, entry: dict[str, Any], at: datetime, paid_amount: Decimal = Decimal("0.00")) -> dict[str, Any]:
        duration_minutes = max(1, math.ceil((_utc_datetime(at) - _utc_datetime(entry["entry_at"])).total_seconds() / 60))
        snapshot = entry.get("rate_snapshot")
        if not snapshot:
            raise ConflictError("The vehicle entry does not contain a tariff snapshot.")
        slab = next(
            (
                item
                for item in snapshot["duration_slabs"]
                if duration_minutes >= item["from_minutes"] and (item.get("to_minutes") is None or duration_minutes < item["to_minutes"])
            ),
            None,
        )
        if not slab:
            raise ConflictError("The vehicle duration is outside the stored tariff slabs.")
        parking_charge = _money(slab["amount"])
        gst_percent = _money(slab["gst_percent"])
        gst_amount = _money(parking_charge * gst_percent / Decimal("100"))
        total_amount = _money(parking_charge + gst_amount)
        advance_amount = _money(entry["advance_amount"])
        advance_applied = min(advance_amount, total_amount)
        payable_after_advance = _money(total_amount - advance_applied)
        paid = _money(paid_amount)
        if paid > payable_after_advance:
            raise ConflictError("Paid amount cannot exceed the outstanding balance.")
        return {
            "duration_minutes": duration_minutes,
            "parking_charge": parking_charge,
            "gst_percent": gst_percent,
            "gst_amount": gst_amount,
            "total_amount": total_amount,
            "advance_amount": advance_amount,
            "advance_applied": advance_applied,
            "paid_amount": paid,
            "balance_amount": _money(payable_after_advance - paid),
            "rate_effective_date": snapshot["effective_date"],
        }

    @staticmethod
    def _public_calculation(values: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
        rate_effective_date = values["rate_effective_date"]
        if isinstance(rate_effective_date, datetime):
            rate_effective_date = rate_effective_date.date()
        return {
            "entry": entry,
            "duration_minutes": values["duration_minutes"],
            "parking_charge": _money_string(values["parking_charge"]),
            "gst_percent": _money_string(values["gst_percent"]),
            "gst_amount": _money_string(values["gst_amount"]),
            "total_amount": _money_string(values["total_amount"]),
            "advance_amount": _money_string(values["advance_amount"]),
            "advance_applied": _money_string(values["advance_applied"]),
            "paid_amount": _money_string(values["paid_amount"]),
            "balance_amount": _money_string(values["balance_amount"]),
            "rate_effective_date": rate_effective_date,
        }

    async def calculate_exit(self, company_id: str, entry_id: str) -> dict[str, Any]:
        company = await self._company(company_id)
        entry = await self.database.vehicle_entries.find_one(
            {"_id": _object_id(entry_id, "Vehicle entry"), "company_id": company["_id"], "status": "open"}
        )
        if not entry:
            raise NotFoundError("An open vehicle entry was not found.")
        return self._public_calculation(
            self._calculation_for_entry(entry, datetime.now(UTC)), await self._public_entry(entry)
        )

    async def create_exit(self, company_id: str, payload: dict[str, Any], actor_id: str) -> dict[str, Any]:
        company = await self._company(company_id)
        entry = await self.database.vehicle_entries.find_one(
            {"_id": _object_id(payload["entry_id"], "Vehicle entry"), "company_id": company["_id"], "status": "open"}
        )
        if not entry:
            raise NotFoundError("An open vehicle entry was not found.")
        now = datetime.now(UTC)
        calculation = self._calculation_for_entry(entry, now, _money(payload["paid_amount"]))
        if calculation["balance_amount"] != Decimal("0.00"):
            raise ConflictError("Collect the complete outstanding balance before completing vehicle exit.")
        exit_id = ObjectId()
        exit_document = {
            "_id": exit_id,
            "company_id": company["_id"],
            "location_id": entry.get("location_id"),
            "entry_id": entry["_id"],
            "token_number": entry["token_number"],
            "vehicle_number": entry["vehicle_number"],
            "vehicle_type": entry["vehicle_type"],
            "exit_at": now,
            "exit_by": _object_id(actor_id, "Actor"),
            **{key: Decimal128(str(value)) if isinstance(value, Decimal) else value for key, value in calculation.items()},
            "payment_method": payload.get("payment_method"),
            "payment_reference": payload.get("payment_reference"),
            "status": "completed",
            "created_at": now,
        }
        payment_document = None
        if calculation["paid_amount"] > Decimal("0.00"):
            payment_document = {
                "company_id": company["_id"],
                "reference_type": "vehicle_exit",
                "reference_id": exit_id,
                "amount": Decimal128(str(calculation["paid_amount"])),
                "method": payload["payment_method"],
                "payment_reference": payload.get("payment_reference"),
                "idempotency_key": f"vehicle-exit:{exit_id}",
                "status": "paid",
                "paid_at": now,
                "created_at": now,
            }
        try:
            if payment_document:
                await self.database.payments.insert_one(payment_document)
            await self.database.vehicle_exits.insert_one(exit_document)
        except DuplicateKeyError as exc:
            if payment_document:
                await self.database.payments.delete_one({"company_id": company["_id"], "idempotency_key": payment_document["idempotency_key"]})
            raise ConflictError("This vehicle entry has already been settled.") from exc
        updated = await self.database.vehicle_entries.update_one(
            {"_id": entry["_id"], "status": "open"},
            {"$set": {"status": "closed", "exit_id": exit_id, "exit_at": now, "updated_at": now}},
        )
        if updated.modified_count != 1:
            await self.database.vehicle_exits.delete_one({"_id": exit_id})
            if payment_document:
                await self.database.payments.delete_one({"company_id": company["_id"], "idempotency_key": payment_document["idempotency_key"]})
            raise ConflictError("Vehicle entry is no longer open.")
        await self._complete_reservation_on_exit(company["_id"], entry, exit_id, now)
        return self._public_exit(exit_document, await self._public_entry({**entry, "status": "closed"}))

    def _public_exit(self, document: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
        values = {
            key: _money_string(document[key])
            for key in ("parking_charge", "gst_percent", "gst_amount", "total_amount", "advance_amount", "advance_applied", "paid_amount", "balance_amount")
        }
        return {
            "id": str(document["_id"]),
            "exit_at": document["exit_at"],
            "payment_method": document.get("payment_method"),
            "payment_reference": document.get("payment_reference"),
            "status": document["status"],
            **self._public_calculation(
                {**document, **{key: _decimal(document[key]) for key in values}, "rate_effective_date": document["rate_effective_date"]}, entry
            ),
        }

    async def exit_log(self, company_id: str, pagination: PaginationParams, search: str | None = None) -> Page[dict[str, Any]]:
        company = await self._company(company_id)
        query: dict[str, Any] = {"company_id": company["_id"]}
        if search and (normalized := self._normalized_vehicle_number(search)):
            pattern = {"$regex": normalized, "$options": "i"}
            query["$or"] = [{"vehicle_number": pattern}, {"token_number": pattern}]
        total = await self.database.vehicle_exits.count_documents(query)
        exits = [item async for item in self.database.vehicle_exits.find(query).sort("exit_at", DESCENDING).skip(pagination.offset).limit(pagination.limit)]
        entries = {
            entry["_id"]: await self._public_entry(entry)
            async for entry in self.database.vehicle_entries.find({"company_id": company["_id"], "_id": {"$in": [item["entry_id"] for item in exits]}})
        }
        return Page.create(
            items=[self._public_exit(item, entries[item["entry_id"]]) for item in exits if item["entry_id"] in entries],
            total=total,
            pagination=pagination,
        )

    @staticmethod
    def _address_text(company: dict[str, Any]) -> str | None:
        address = company.get("address") or {}
        values = [address.get(key) for key in ("line1", "line2", "city", "state", "postal_code", "country_code")]
        parts = [str(value).strip() for value in values if value]
        return ", ".join(parts) or None

    def _receipt_company(self, company: dict[str, Any]) -> dict[str, Any]:
        return {
            "company_name": company["company_name"],
            "logo_url": company.get("logo_url") or company.get("theme", {}).get("logo_url"),
            "gstin": company.get("gstin"),
            "address": self._address_text(company),
            "currency": company.get("currency", "INR"),
            "receipt_footer": company.get("receipt_footer"),
        }

    async def _receipt_operator(self, company_id: ObjectId, actor_id: ObjectId | None) -> dict[str, str | None]:
        if not actor_id:
            return {"name": "System", "employee_id": None, "designation": None}
        employee, user = await asyncio.gather(
            self.database.employees.find_one({"company_id": company_id, "user_id": actor_id}),
            self.database.users.find_one({"_id": actor_id, "company_id": company_id}),
        )
        if employee:
            return {
                "name": employee.get("name") or "Parking operator",
                "employee_id": employee.get("employee_id"),
                "designation": employee.get("designation"),
            }
        return {
            "name": (user or {}).get("name") or (user or {}).get("full_name") or (user or {}).get("username") or "System",
            "employee_id": None,
            "designation": None,
        }

    @staticmethod
    def _receipt_identifiers(receipt_type: str, token_number: str) -> dict[str, str]:
        prefix = "EN" if receipt_type == "entry" else "EX"
        receipt_number = f"{prefix}-{token_number}"
        return {"receipt_number": receipt_number, "qr_payload": receipt_number, "barcode_value": receipt_number}

    async def entry_receipt(self, company_id: str, entry_id: str) -> dict[str, Any]:
        receipt_id = _receipt_object_id(entry_id, "Vehicle entry")
        try:
            company = await self._company(company_id)
            entry = await self.database.vehicle_entries.find_one({"_id": receipt_id, "company_id": company["_id"]})
            if not entry:
                raise NotFoundError("Vehicle entry receipt was not found.")
            identifiers = self._receipt_identifiers("entry", entry["token_number"])
            return {
                "receipt_type": "entry",
                **identifiers,
                "issued_at": datetime.now(UTC),
                "company": self._receipt_company(company),
                "operator": await self._receipt_operator(company["_id"], entry.get("entry_by")),
                "entry": await self._public_entry(entry),
                "exit": None,
            }
        except PyMongoError as exc:
            logger.exception("Database error while retrieving vehicle entry receipt")
            raise DatabaseUnavailableError("Vehicle entry receipt is temporarily unavailable. Please retry.") from exc

    async def exit_receipt(self, company_id: str, exit_id: str) -> dict[str, Any]:
        receipt_id = _receipt_object_id(exit_id, "Vehicle exit")
        try:
            company = await self._company(company_id)
            exit = await self.database.vehicle_exits.find_one({"_id": receipt_id, "company_id": company["_id"]})
            if not exit:
                raise NotFoundError("Vehicle exit receipt was not found.")
            entry = await self.database.vehicle_entries.find_one({"_id": exit["entry_id"], "company_id": company["_id"]})
            if not entry:
                raise NotFoundError("Vehicle entry data for this exit receipt was not found.")
            public_entry = await self._public_entry(entry)
            identifiers = self._receipt_identifiers("exit", exit["token_number"])
            return {
                "receipt_type": "exit",
                **identifiers,
                "issued_at": datetime.now(UTC),
                "company": self._receipt_company(company),
                "operator": await self._receipt_operator(company["_id"], exit.get("exit_by")),
                "entry": public_entry,
                "exit": self._public_exit(exit, public_entry),
            }
        except PyMongoError as exc:
            logger.exception("Database error while retrieving vehicle exit receipt")
            raise DatabaseUnavailableError("Vehicle exit receipt is temporarily unavailable. Please retry.") from exc

    async def entry_image(self, company_id: str, entry_id: str) -> tuple[bytes, str]:
        company = await self._company(company_id)
        entry = await self.database.vehicle_entries.find_one({"_id": _object_id(entry_id, "Vehicle entry"), "company_id": company["_id"]})
        if not entry or not entry.get("vehicle_image_file_id"):
            raise NotFoundError("Vehicle image was not found.")
        try:
            stream = await AsyncIOMotorGridFSBucket(self.database, bucket_name="vehicle_images").open_download_stream(entry["vehicle_image_file_id"])
            content = await stream.read()
        except NoFile as exc:
            raise NotFoundError("Vehicle image was not found.") from exc
        return content, stream.metadata.get("content_type", "application/octet-stream")
