from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from bson import ObjectId
from bson.decimal128 import Decimal128
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING
from pymongo.errors import PyMongoError

from app.core.exceptions import DatabaseUnavailableError, NotFoundError
from app.shared.constants import VEHICLE_TYPES

logger = logging.getLogger(__name__)


def _decimal(value: Any) -> Decimal:
    return value.to_decimal() if isinstance(value, Decimal128) else Decimal(str(value or "0"))


def _money(value: Any) -> str:
    return f"{_decimal(value).quantize(Decimal('0.01')):.2f}"


class DashboardService:
    """Read-only tenant dashboard aggregates for operational parking data."""

    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.database = database

    async def _company(self, company_id: str) -> dict[str, Any]:
        if not ObjectId.is_valid(company_id):
            raise NotFoundError("Company was not found.")
        company = await self.database.companies.find_one({"_id": ObjectId(company_id), "status": "active"})
        if not company:
            raise NotFoundError("Company was not found or is inactive.")
        return company

    @staticmethod
    def _timezone(company: dict[str, Any]) -> ZoneInfo:
        try:
            return ZoneInfo(company.get("timezone", "Asia/Kolkata"))
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")

    @staticmethod
    def _day_start(now: datetime, timezone: ZoneInfo, days_ago: int = 0) -> datetime:
        local = now.astimezone(timezone).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_ago)
        return local.astimezone(UTC)

    async def _sum(self, collection: str, query: dict[str, Any], field: str) -> Decimal:
        result = await self.database[collection].aggregate(
            [{"$match": query}, {"$group": {"_id": None, "total": {"$sum": f"${field}"}}}]
        ).to_list(1)
        return _decimal(result[0]["total"]) if result else Decimal("0")

    async def overview(self, company_id: str) -> dict[str, Any]:
        try:
            company = await self._company(company_id)
            company_object_id = company["_id"]
            now = datetime.now(UTC)
            timezone = self._timezone(company)
            today_start = self._day_start(now, timezone)
            tomorrow_start = self._day_start(now, timezone, -1)
            week_start = self._day_start(now, timezone, 6)
            local_month_start = now.astimezone(timezone).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_start = local_month_start.astimezone(UTC)
            today_range = {"$gte": today_start, "$lt": tomorrow_start}

            (
                today_entries,
                today_exits,
                active_entries,
                capacity_result,
                collected_payments,
                collected_advances,
                monthly_revenue,
                weekly_revenue,
            ) = await asyncio.gather(
                self.database.vehicle_entries.count_documents({"company_id": company_object_id, "entry_at": today_range}),
                self.database.vehicle_exits.count_documents({"company_id": company_object_id, "exit_at": today_range}),
                self.database.vehicle_entries.count_documents({"company_id": company_object_id, "status": "open"}),
                self.database.parking_locations.aggregate(
                    [{"$match": {"company_id": company_object_id, "status": "active"}}, {"$group": {"_id": None, "total": {"$sum": "$capacity"}}}]
                ).to_list(1),
                self._sum("payments", {"company_id": company_object_id, "status": "paid", "paid_at": today_range}, "amount"),
                self._sum("vehicle_entries", {"company_id": company_object_id, "entry_at": today_range}, "advance_amount"),
                self._sum("vehicle_exits", {"company_id": company_object_id, "exit_at": {"$gte": month_start, "$lt": tomorrow_start}}, "total_amount"),
                self._sum("vehicle_exits", {"company_id": company_object_id, "exit_at": {"$gte": week_start, "$lt": tomorrow_start}}, "total_amount"),
            )
            capacity = int(capacity_result[0]["total"]) if capacity_result else 0
            revenue, vehicle_types, occupancy, recent_activities = await asyncio.gather(
                self._revenue_series(company_object_id, now, timezone),
                self._vehicle_types(company_object_id, month_start, tomorrow_start),
                self._occupancy(company_object_id),
                self._recent_activities(company_object_id, today_range),
            )
            return {
                "currency": company.get("currency", "INR"),
                "today_collection": _money(collected_payments + collected_advances),
                "today_entries": today_entries,
                "today_exits": today_exits,
                "monthly_revenue": _money(monthly_revenue),
                "weekly_revenue": _money(weekly_revenue),
                "occupied_slots": active_entries,
                "available_slots": max(capacity - active_entries, 0),
                "revenue": revenue,
                "vehicle_types": vehicle_types,
                "occupancy": occupancy,
                "recent_activities": recent_activities,
            }
        except PyMongoError as exc:
            logger.exception("Database error while building dashboard overview")
            raise DatabaseUnavailableError("Dashboard data is temporarily unavailable. Please retry.") from exc

    async def _revenue_series(self, company_id: ObjectId, now: datetime, timezone: ZoneInfo) -> list[dict[str, str]]:
        starts = [self._day_start(now, timezone, offset) for offset in range(6, -1, -1)]
        totals = await asyncio.gather(
            *[
                self._sum("vehicle_exits", {"company_id": company_id, "exit_at": {"$gte": start, "$lt": end}}, "total_amount")
                for start, end in zip(starts, [*starts[1:], self._day_start(now, timezone, -1)], strict=True)
            ]
        )
        return [
            {"date": start.astimezone(timezone).date().isoformat(), "label": start.astimezone(timezone).strftime("%a"), "amount": _money(total)}
            for start, total in zip(starts, totals, strict=True)
        ]

    async def _vehicle_types(self, company_id: ObjectId, month_start: datetime, tomorrow_start: datetime) -> list[dict[str, Any]]:
        documents = await self.database.vehicle_entries.aggregate(
            [
                {"$match": {"company_id": company_id, "entry_at": {"$gte": month_start, "$lt": tomorrow_start}}},
                {"$group": {"_id": "$vehicle_type", "count": {"$sum": 1}}},
            ]
        ).to_list(None)
        counts = {item["_id"]: int(item["count"]) for item in documents}
        return [{"vehicle_type": vehicle_type, "count": counts.get(vehicle_type, 0)} for vehicle_type in VEHICLE_TYPES]

    async def _occupancy(self, company_id: ObjectId) -> list[dict[str, Any]]:
        locations, documents = await asyncio.gather(
            self.database.parking_locations.find({"company_id": company_id, "status": "active"}).sort("name", 1).to_list(None),
            self.database.vehicle_entries.aggregate(
                [
                    {"$match": {"company_id": company_id, "status": "open"}},
                    {"$group": {"_id": "$location_id", "occupied": {"$sum": 1}}},
                ]
            ).to_list(None),
        )
        occupied = {item["_id"]: int(item["occupied"]) for item in documents}
        statuses = [
            {
                "location_id": str(location["_id"]),
                "location_name": location["name"],
                "capacity": int(location.get("capacity", 0)),
                "occupied": occupied.get(location["_id"], 0),
                "available": max(int(location.get("capacity", 0)) - occupied.get(location["_id"], 0), 0),
            }
            for location in locations
        ]
        unassigned = occupied.get(None, 0)
        if unassigned:
            statuses.append({"location_id": None, "location_name": "Unassigned", "capacity": 0, "occupied": unassigned, "available": 0})
        return statuses

    async def _recent_activities(self, company_id: ObjectId, today_range: dict[str, datetime]) -> list[dict[str, Any]]:
        entries, exits, locations = await asyncio.gather(
            self.database.vehicle_entries.find({"company_id": company_id, "entry_at": today_range}).sort("entry_at", DESCENDING).limit(6).to_list(6),
            self.database.vehicle_exits.find({"company_id": company_id, "exit_at": today_range}).sort("exit_at", DESCENDING).limit(6).to_list(6),
            self.database.parking_locations.find({"company_id": company_id}).to_list(None),
        )
        location_names = {location["_id"]: location["name"] for location in locations}
        activities = [
            {
                "id": f"entry:{entry['_id']}",
                "kind": "entry",
                "vehicle_number": entry["vehicle_number"],
                "token_number": entry["token_number"],
                "occurred_at": entry["entry_at"],
                "location_name": location_names.get(entry.get("location_id")),
                "amount": _money(entry["advance_amount"]) if _decimal(entry["advance_amount"]) else None,
            }
            for entry in entries
        ] + [
            {
                "id": f"exit:{vehicle_exit['_id']}",
                "kind": "exit",
                "vehicle_number": vehicle_exit["vehicle_number"],
                "token_number": vehicle_exit["token_number"],
                "occurred_at": vehicle_exit["exit_at"],
                "location_name": location_names.get(vehicle_exit.get("location_id")),
                "amount": _money(vehicle_exit["total_amount"]),
            }
            for vehicle_exit in exits
        ]
        return sorted(activities, key=lambda item: item["occurred_at"], reverse=True)[:8]
