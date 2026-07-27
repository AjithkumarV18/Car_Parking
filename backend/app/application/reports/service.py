from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Awaitable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, TypeVar
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from bson import ObjectId
from bson.decimal128 import Decimal128
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING
from pymongo.errors import PyMongoError

from app.api.v1.schemas.reports import ReportFilters, ReportName
from app.core.exceptions import DatabaseUnavailableError, NotFoundError
from app.shared.pagination import Page, PaginationParams

logger = logging.getLogger(__name__)

MONEY_QUANTUM = Decimal("0.01")
MAX_EXPORT_ROWS = 10_000
ResultT = TypeVar("ResultT")


def _decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal128):
        return value.to_decimal()
    return Decimal(str(0 if value is None else value))


def _money(value: Any) -> str:
    return f"{_decimal(value).quantize(MONEY_QUANTUM):.2f}"


@dataclass(frozen=True)
class _Criteria:
    date_from: date
    date_to: date
    start_at: datetime
    end_at: datetime
    timezone: ZoneInfo
    location_id: ObjectId | None
    vehicle_type: str | None
    payment_method: str | None
    search: str | None


class ReportService:
    """Read-only tenant reporting service over operational parking collections."""

    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.database = database

    async def _safe(self, report_name: str, operation: Awaitable[ResultT]) -> ResultT:
        try:
            return await operation
        except PyMongoError as exc:
            logger.exception("Database error while preparing %s", report_name)
            raise DatabaseUnavailableError("Report data is temporarily unavailable. Please retry.") from exc

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
    def _utc_day_boundary(value: date, timezone: ZoneInfo) -> datetime:
        return datetime.combine(value, time.min, tzinfo=timezone).astimezone(UTC)

    async def _criteria(self, company_id: str, filters: ReportFilters) -> tuple[dict[str, Any], _Criteria]:
        company = await self._company(company_id)
        timezone = self._timezone(company)
        today = datetime.now(UTC).astimezone(timezone).date()
        date_from = filters.date_from or today.replace(day=1)
        date_to = filters.date_to or today
        criteria = _Criteria(
            date_from=date_from,
            date_to=date_to,
            start_at=self._utc_day_boundary(date_from, timezone),
            end_at=self._utc_day_boundary(date_to + timedelta(days=1), timezone),
            timezone=timezone,
            location_id=ObjectId(filters.location_id) if filters.location_id else None,
            vehicle_type=filters.vehicle_type,
            payment_method=filters.payment_method,
            search=filters.search,
        )
        return company, criteria

    @staticmethod
    def _search_conditions(search: str | None, fields: tuple[str, ...]) -> list[dict[str, Any]]:
        if not search:
            return []
        pattern = {"$regex": re.escape(search), "$options": "i"}
        return [{field: pattern} for field in fields]

    def _exit_match(self, company_id: ObjectId, criteria: _Criteria) -> dict[str, Any]:
        query: dict[str, Any] = {
            "company_id": company_id,
            "status": "completed",
            "exit_at": {"$gte": criteria.start_at, "$lt": criteria.end_at},
        }
        if criteria.location_id:
            query["location_id"] = criteria.location_id
        if criteria.vehicle_type:
            query["vehicle_type"] = criteria.vehicle_type
        if conditions := self._search_conditions(criteria.search, ("vehicle_number", "token_number")):
            query["$or"] = conditions
        return query

    def _entry_match(self, company_id: ObjectId, criteria: _Criteria) -> dict[str, Any]:
        query: dict[str, Any] = {
            "company_id": company_id,
            "entry_at": {"$gte": criteria.start_at, "$lt": criteria.end_at},
            "advance_amount": {"$gt": Decimal128("0")},
        }
        if criteria.location_id:
            query["location_id"] = criteria.location_id
        if criteria.vehicle_type:
            query["vehicle_type"] = criteria.vehicle_type
        if conditions := self._search_conditions(criteria.search, ("vehicle_number", "token_number", "parking_number")):
            query["$or"] = conditions
        return query

    def _payment_pipeline(self, company_id: ObjectId, criteria: _Criteria) -> list[dict[str, Any]]:
        match: dict[str, Any] = {
            "company_id": company_id,
            "status": "paid",
            "paid_at": {"$gte": criteria.start_at, "$lt": criteria.end_at},
        }
        if criteria.payment_method:
            match["method"] = criteria.payment_method
        pipeline: list[dict[str, Any]] = [
            {"$match": match},
            {
                "$lookup": {
                    "from": "vehicle_exits",
                    "localField": "reference_id",
                    "foreignField": "_id",
                    "as": "vehicle_exit",
                }
            },
            {"$unwind": "$vehicle_exit"},
            {"$match": {"vehicle_exit.company_id": company_id, "vehicle_exit.status": "completed"}},
        ]
        vehicle_match: dict[str, Any] = {}
        if criteria.location_id:
            vehicle_match["vehicle_exit.location_id"] = criteria.location_id
        if criteria.vehicle_type:
            vehicle_match["vehicle_exit.vehicle_type"] = criteria.vehicle_type
        if conditions := self._search_conditions(
            criteria.search, ("vehicle_exit.vehicle_number", "vehicle_exit.token_number")
        ):
            vehicle_match["$or"] = conditions
        if vehicle_match:
            pipeline.append({"$match": vehicle_match})
        return pipeline

    @staticmethod
    def _period_expression(field: str, criteria: _Criteria, date_format: str) -> dict[str, Any]:
        return {"$dateToString": {"format": date_format, "date": f"${field}", "timezone": criteria.timezone.key}}

    async def _collection_rows(self, company: dict[str, Any], criteria: _Criteria, *, monthly: bool) -> list[dict[str, Any]]:
        company_id = company["_id"]
        date_format = "%Y-%m" if monthly else "%Y-%m-%d"
        payment_pipeline = [
            *self._payment_pipeline(company_id, criteria),
            {
                "$group": {
                    "_id": self._period_expression("paid_at", criteria, date_format),
                    "settlement_collection": {"$sum": "$amount"},
                }
            },
        ]
        advance_pipeline = [
            {"$match": self._entry_match(company_id, criteria)},
            {
                "$group": {
                    "_id": self._period_expression("entry_at", criteria, date_format),
                    "advance_collection": {"$sum": "$advance_amount"},
                }
            },
        ]
        exit_pipeline = [
            {"$match": self._exit_match(company_id, criteria)},
            {
                "$group": {
                    "_id": self._period_expression("exit_at", criteria, date_format),
                    "exit_revenue": {"$sum": "$total_amount"},
                    "gst_amount": {"$sum": "$gst_amount"},
                    "exit_count": {"$sum": 1},
                }
            },
        ]
        payments, advances, exits = await asyncio.gather(
            self.database.payments.aggregate(payment_pipeline).to_list(None),
            self.database.vehicle_entries.aggregate(advance_pipeline).to_list(None),
            self.database.vehicle_exits.aggregate(exit_pipeline).to_list(None),
        )
        values: dict[str, dict[str, Any]] = {}
        for row in payments:
            values.setdefault(row["_id"], {})["settlement_collection"] = _decimal(row["settlement_collection"])
        for row in advances:
            values.setdefault(row["_id"], {})["advance_collection"] = _decimal(row["advance_collection"])
        for row in exits:
            current = values.setdefault(row["_id"], {})
            current["exit_revenue"] = _decimal(row["exit_revenue"])
            current["gst_amount"] = _decimal(row["gst_amount"])
            current["exit_count"] = int(row["exit_count"])

        periods = self._periods(criteria, monthly=monthly)
        output: list[dict[str, Any]] = []
        for period in periods:
            current = values.get(period, {})
            settlement = current.get("settlement_collection", Decimal("0"))
            advance = current.get("advance_collection", Decimal("0"))
            row = {
                "period": period if monthly else date.fromisoformat(period),
                "settlement_collection": _money(settlement),
                "advance_collection": _money(advance),
                "total_collection": _money(settlement + advance),
                "exit_revenue": _money(current.get("exit_revenue", Decimal("0"))),
                "gst_amount": _money(current.get("gst_amount", Decimal("0"))),
                "exit_count": current.get("exit_count", 0),
            }
            output.append(row)
        return output

    @staticmethod
    def _periods(criteria: _Criteria, *, monthly: bool) -> list[str]:
        if not monthly:
            total_days = (criteria.date_to - criteria.date_from).days
            return [(criteria.date_from + timedelta(days=offset)).isoformat() for offset in range(total_days + 1)]
        current = criteria.date_from.replace(day=1)
        final = criteria.date_to.replace(day=1)
        values: list[str] = []
        while current <= final:
            values.append(current.strftime("%Y-%m"))
            current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        return values

    async def overview(self, company_id: str, filters: ReportFilters) -> dict[str, Any]:
        return await self._safe("report overview", self._overview(company_id, filters))

    async def _overview(self, company_id: str, filters: ReportFilters) -> dict[str, Any]:
        company, criteria = await self._criteria(company_id, filters)
        daily_rows, payment_methods = await asyncio.gather(
            self._collection_rows(company, criteria, monthly=False), self._payment_methods(company["_id"], criteria)
        )
        total_collection = sum((_decimal(row["total_collection"]) for row in daily_rows), Decimal("0"))
        advance_collection = sum((_decimal(row["advance_collection"]) for row in daily_rows), Decimal("0"))
        settlement_collection = sum((_decimal(row["settlement_collection"]) for row in daily_rows), Decimal("0"))
        gst_collected = sum((_decimal(row["gst_amount"]) for row in daily_rows), Decimal("0"))
        return {
            "currency": company.get("currency", "INR"),
            "date_from": criteria.date_from,
            "date_to": criteria.date_to,
            "total_collection": _money(total_collection),
            "advance_collection": _money(advance_collection),
            "settlement_collection": _money(settlement_collection),
            "completed_exits": sum(int(row["exit_count"]) for row in daily_rows),
            "gst_collected": _money(gst_collected),
            "revenue": [
                {
                    "period": row["period"].isoformat(),
                    "label": row["period"].strftime("%d %b"),
                    "amount": row["total_collection"],
                }
                for row in daily_rows
            ],
            "payment_methods": payment_methods,
        }

    async def _payment_methods(self, company_id: ObjectId, criteria: _Criteria) -> list[dict[str, Any]]:
        pipeline = [
            *self._payment_pipeline(company_id, criteria),
            {"$group": {"_id": "$method", "amount": {"$sum": "$amount"}, "count": {"$sum": 1}}},
        ]
        documents = await self.database.payments.aggregate(pipeline).to_list(None)
        values = {item["_id"]: item for item in documents}
        return [
            {"method": method, "amount": _money(values.get(method, {}).get("amount", 0)), "count": int(values.get(method, {}).get("count", 0))}
            for method in ("cash", "upi", "card")
        ]

    async def daily_collection(self, company_id: str, filters: ReportFilters) -> list[dict[str, Any]]:
        return await self._safe("daily collection report", self._collection_report(company_id, filters, monthly=False))

    async def monthly_collection(self, company_id: str, filters: ReportFilters) -> list[dict[str, Any]]:
        return await self._safe("monthly collection report", self._collection_report(company_id, filters, monthly=True))

    async def _collection_report(self, company_id: str, filters: ReportFilters, *, monthly: bool) -> list[dict[str, Any]]:
        company, criteria = await self._criteria(company_id, filters)
        return await self._collection_rows(company, criteria, monthly=monthly)

    async def vehicles(
        self, company_id: str, filters: ReportFilters, pagination: PaginationParams
    ) -> dict[str, Any]:
        return await self._safe("vehicle report", self._vehicles(company_id, filters, pagination))

    async def _vehicles(self, company_id: str, filters: ReportFilters, pagination: PaginationParams) -> dict[str, Any]:
        company, criteria = await self._criteria(company_id, filters)
        match = self._exit_match(company["_id"], criteria)
        total, documents = await asyncio.gather(
            self.database.vehicle_exits.count_documents(match),
            self.database.vehicle_exits.find(match)
            .sort("exit_at", DESCENDING)
            .skip(pagination.offset)
            .limit(pagination.limit)
            .to_list(pagination.limit),
        )
        entry_ids = [document["entry_id"] for document in documents if document.get("entry_id")]
        location_ids = [document["location_id"] for document in documents if document.get("location_id")]
        entries, location_names = await asyncio.gather(
            self.database.vehicle_entries.find({"_id": {"$in": entry_ids}, "company_id": company["_id"]}).to_list(None)
            if entry_ids
            else _empty_list(),
            self._location_names(company["_id"], location_ids),
        )
        entry_by_id = {entry["_id"]: entry for entry in entries}
        rows = []
        for vehicle_exit in documents:
            entry = entry_by_id.get(vehicle_exit.get("entry_id"), {})
            rows.append(
                {
                    "id": str(vehicle_exit["_id"]),
                    "vehicle_number": vehicle_exit["vehicle_number"],
                    "vehicle_type": vehicle_exit["vehicle_type"],
                    "token_number": vehicle_exit["token_number"],
                    "parking_number": entry.get("parking_number"),
                    "entry_at": entry.get("entry_at"),
                    "exit_at": vehicle_exit["exit_at"],
                    "duration_minutes": int(vehicle_exit.get("duration_minutes", 0)),
                    "parking_charge": _money(vehicle_exit.get("parking_charge")),
                    "gst_amount": _money(vehicle_exit.get("gst_amount")),
                    "total_amount": _money(vehicle_exit.get("total_amount")),
                    "advance_applied": _money(vehicle_exit.get("advance_applied")),
                    "paid_amount": _money(vehicle_exit.get("paid_amount")),
                    "payment_method": vehicle_exit.get("payment_method"),
                    "location_name": location_names.get(vehicle_exit.get("location_id")),
                    "status": "completed",
                }
            )
        return Page.create(items=rows, total=total, pagination=pagination).model_dump(mode="python")

    async def employee_collection(self, company_id: str, filters: ReportFilters) -> list[dict[str, Any]]:
        return await self._safe("employee collection report", self._employee_collection(company_id, filters))

    async def _employee_collection(self, company_id: str, filters: ReportFilters) -> list[dict[str, Any]]:
        company, criteria = await self._criteria(company_id, filters)
        documents = await self.database.vehicle_exits.aggregate(
            [
                {"$match": self._exit_match(company["_id"], criteria)},
                {
                    "$group": {
                        "_id": "$exit_by",
                        "exits_completed": {"$sum": 1},
                        "settlement_collection": {"$sum": "$paid_amount"},
                        "advance_applied": {"$sum": "$advance_applied"},
                        "total_revenue": {"$sum": "$total_amount"},
                        "gst_amount": {"$sum": "$gst_amount"},
                    }
                },
            ]
        ).to_list(None)
        actors = await self._actors(company["_id"], [document["_id"] for document in documents if document.get("_id")])
        rows = []
        for document in documents:
            actor = actors.get(document.get("_id"), {})
            rows.append(
                {
                    "employee_id": actor.get("employee_id"),
                    "employee_name": actor.get("name", "Unassigned operator"),
                    "designation": actor.get("designation"),
                    "exits_completed": int(document["exits_completed"]),
                    "settlement_collection": _money(document["settlement_collection"]),
                    "advance_applied": _money(document["advance_applied"]),
                    "total_revenue": _money(document["total_revenue"]),
                    "gst_amount": _money(document["gst_amount"]),
                }
            )
        return sorted(rows, key=lambda row: Decimal(row["total_revenue"]), reverse=True)

    async def gst(self, company_id: str, filters: ReportFilters) -> list[dict[str, Any]]:
        return await self._safe("GST report", self._gst(company_id, filters))

    async def _gst(self, company_id: str, filters: ReportFilters) -> list[dict[str, Any]]:
        company, criteria = await self._criteria(company_id, filters)
        documents = await self.database.vehicle_exits.aggregate(
            [
                {"$match": self._exit_match(company["_id"], criteria)},
                {
                    "$group": {
                        "_id": self._period_expression("exit_at", criteria, "%Y-%m-%d"),
                        "parking_charge": {"$sum": "$parking_charge"},
                        "gst_amount": {"$sum": "$gst_amount"},
                        "total_amount": {"$sum": "$total_amount"},
                        "exits_completed": {"$sum": 1},
                    }
                },
            ]
        ).to_list(None)
        by_period = {document["_id"]: document for document in documents}
        return [
            {
                "period": date.fromisoformat(period),
                "parking_charge": _money(by_period.get(period, {}).get("parking_charge", 0)),
                "gst_amount": _money(by_period.get(period, {}).get("gst_amount", 0)),
                "total_amount": _money(by_period.get(period, {}).get("total_amount", 0)),
                "exits_completed": int(by_period.get(period, {}).get("exits_completed", 0)),
            }
            for period in self._periods(criteria, monthly=False)
        ]

    async def audit(self, company_id: str, filters: ReportFilters, pagination: PaginationParams) -> dict[str, Any]:
        return await self._safe("audit report", self._audit(company_id, filters, pagination))

    async def _audit(self, company_id: str, filters: ReportFilters, pagination: PaginationParams) -> dict[str, Any]:
        company, criteria = await self._criteria(company_id, filters)
        match: dict[str, Any] = {
            "company_id": company["_id"],
            "occurred_at": {"$gte": criteria.start_at, "$lt": criteria.end_at},
        }
        if criteria.search:
            match["$or"] = self._search_conditions(criteria.search, ("action", "entity_type", "entity_id"))
        total, documents = await asyncio.gather(
            self.database.audit_logs.count_documents(match),
            self.database.audit_logs.find(match)
            .sort("occurred_at", DESCENDING)
            .skip(pagination.offset)
            .limit(pagination.limit)
            .to_list(pagination.limit),
        )
        actors = await self._actors(company["_id"], [document.get("actor_id") for document in documents if document.get("actor_id")])
        rows = [
            {
                "id": str(document["_id"]),
                "occurred_at": document["occurred_at"],
                "actor_name": actors.get(document.get("actor_id"), {}).get("name"),
                "action": document.get("action", "Unknown"),
                "entity_type": document.get("entity_type", "Unknown"),
                "entity_id": str(document["entity_id"]) if document.get("entity_id") else None,
                "outcome": document.get("outcome", "success"),
                "details": document.get("details"),
            }
            for document in documents
        ]
        return Page.create(items=rows, total=total, pagination=pagination).model_dump(mode="python")

    async def payments(self, company_id: str, filters: ReportFilters, pagination: PaginationParams) -> dict[str, Any]:
        return await self._safe("payment report", self._payments(company_id, filters, pagination))

    async def _payments(self, company_id: str, filters: ReportFilters, pagination: PaginationParams) -> dict[str, Any]:
        company, criteria = await self._criteria(company_id, filters)
        pipeline = [
            *self._payment_pipeline(company["_id"], criteria),
            {"$sort": {"paid_at": -1}},
            {
                "$facet": {
                    "items": [{"$skip": pagination.offset}, {"$limit": pagination.limit}],
                    "meta": [{"$count": "total"}],
                }
            },
        ]
        result = await self.database.payments.aggregate(pipeline).to_list(1)
        page = result[0] if result else {"items": [], "meta": []}
        documents = page["items"]
        location_names = await self._location_names(
            company["_id"], [document["vehicle_exit"].get("location_id") for document in documents]
        )
        rows = [
            {
                "id": str(document["_id"]),
                "paid_at": document["paid_at"],
                "vehicle_number": document["vehicle_exit"].get("vehicle_number"),
                "token_number": document["vehicle_exit"].get("token_number"),
                "amount": _money(document["amount"]),
                "method": document["method"],
                "payment_reference": document.get("payment_reference"),
                "status": "paid",
                "location_name": location_names.get(document["vehicle_exit"].get("location_id")),
            }
            for document in documents
        ]
        total = int(page["meta"][0]["total"]) if page["meta"] else 0
        return Page.create(items=rows, total=total, pagination=pagination).model_dump(mode="python")

    async def cancelled_receipts(
        self, company_id: str, filters: ReportFilters, pagination: PaginationParams
    ) -> dict[str, Any]:
        return await self._safe("cancelled receipt report", self._cancelled_receipts(company_id, filters, pagination))

    async def _cancelled_receipts(self, company_id: str, filters: ReportFilters, pagination: PaginationParams) -> dict[str, Any]:
        company, criteria = await self._criteria(company_id, filters)
        match: dict[str, Any] = {
            "company_id": company["_id"],
            "status": "cancelled",
            "cancelled_at": {"$gte": criteria.start_at, "$lt": criteria.end_at},
        }
        if criteria.vehicle_type:
            match["vehicle_type"] = criteria.vehicle_type
        if criteria.search:
            match["$or"] = self._search_conditions(criteria.search, ("vehicle_number", "token_number", "receipt_number"))
        total, documents = await asyncio.gather(
            self.database.cancelled_receipts.count_documents(match),
            self.database.cancelled_receipts.find(match)
            .sort("cancelled_at", DESCENDING)
            .skip(pagination.offset)
            .limit(pagination.limit)
            .to_list(pagination.limit),
        )
        actors = await self._actors(company["_id"], [document.get("cancelled_by") for document in documents if document.get("cancelled_by")])
        rows = [
            {
                "id": str(document["_id"]),
                "receipt_type": document.get("receipt_type", "exit"),
                "receipt_number": document.get("receipt_number"),
                "vehicle_number": document.get("vehicle_number"),
                "token_number": document.get("token_number"),
                "cancelled_at": document["cancelled_at"],
                "cancelled_by_name": actors.get(document.get("cancelled_by"), {}).get("name"),
                "reason": document.get("reason"),
                "amount": _money(document["amount"]) if document.get("amount") is not None else None,
                "status": "cancelled",
            }
            for document in documents
        ]
        return Page.create(items=rows, total=total, pagination=pagination).model_dump(mode="python")

    async def export_rows(self, report_name: ReportName, company_id: str, filters: ReportFilters) -> list[dict[str, Any]]:
        return await self._safe("report export", self._export_rows(report_name, company_id, filters))

    async def _export_rows(self, report_name: ReportName, company_id: str, filters: ReportFilters) -> list[dict[str, Any]]:
        # Exports use a service-owned cap that is intentionally larger than the public
        # query-page limit. The values are constants here, not untrusted request input.
        export_pagination = PaginationParams.model_construct(page=1, limit=MAX_EXPORT_ROWS)
        if report_name == "daily-collection":
            return await self._collection_report(company_id, filters, monthly=False)
        if report_name == "monthly-collection":
            return await self._collection_report(company_id, filters, monthly=True)
        if report_name == "employee-collection":
            return await self._employee_collection(company_id, filters)
        if report_name == "gst":
            return await self._gst(company_id, filters)
        if report_name == "vehicle":
            return (await self._vehicles(company_id, filters, export_pagination))["items"]
        if report_name == "audit":
            return (await self._audit(company_id, filters, export_pagination))["items"]
        if report_name == "payment":
            return (await self._payments(company_id, filters, export_pagination))["items"]
        return (await self._cancelled_receipts(company_id, filters, export_pagination))["items"]

    async def _location_names(self, company_id: ObjectId, location_ids: list[ObjectId | None]) -> dict[ObjectId, str]:
        ids = list({location_id for location_id in location_ids if location_id})
        if not ids:
            return {}
        locations = await self.database.parking_locations.find({"_id": {"$in": ids}, "company_id": company_id}).to_list(None)
        return {location["_id"]: location["name"] for location in locations}

    async def _actors(self, company_id: ObjectId, actor_ids: list[ObjectId | None]) -> dict[ObjectId, dict[str, str | None]]:
        ids = list({actor_id for actor_id in actor_ids if actor_id})
        if not ids:
            return {}
        employees, users = await asyncio.gather(
            self.database.employees.find({"company_id": company_id, "user_id": {"$in": ids}}).to_list(None),
            self.database.users.find({"_id": {"$in": ids}, "company_id": company_id}).to_list(None),
        )
        output = {
            employee["user_id"]: {
                "employee_id": employee.get("employee_id"),
                "name": employee.get("name"),
                "designation": employee.get("designation"),
            }
            for employee in employees
        }
        for user in users:
            output.setdefault(
                user["_id"],
                {
                    "employee_id": None,
                    "name": user.get("name") or user.get("full_name") or user.get("username"),
                    "designation": None,
                },
            )
        return output


async def _empty_list() -> list[dict[str, Any]]:
    return []
