from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from bson import ObjectId
from bson.decimal128 import Decimal128
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING
from pymongo.errors import PyMongoError

from app.api.v1.schemas.audit import AuditLogFilters
from app.core.exceptions import DatabaseUnavailableError, NotFoundError
from app.shared.pagination import Page, PaginationParams

logger = logging.getLogger(__name__)

SENSITIVE_FIELD_MARKERS = ("password", "token", "secret", "authorization", "image_data")
MAX_AUDIT_VALUE_LENGTH = 2_000


def sanitize_audit_value(value: Any, *, field_name: str | None = None) -> Any:
    """Keep audit data searchable while preventing credential and oversized-data retention."""

    if field_name and any(marker in field_name.lower() for marker in SENSITIVE_FIELD_MARKERS):
        return "[REDACTED]"
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, Decimal128):
        return str(value.to_decimal())
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): sanitize_audit_value(item, field_name=str(key)) for key, item in value.items() if str(key) != "_id"}
    if isinstance(value, (list, tuple)):
        return [sanitize_audit_value(item) for item in value[:100]]
    if isinstance(value, str):
        return value[:MAX_AUDIT_VALUE_LENGTH] + ("…" if len(value) > MAX_AUDIT_VALUE_LENGTH else "")
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:MAX_AUDIT_VALUE_LENGTH]


class AuditLogService:
    """Tenant audit query service plus a non-blocking persistence primitive."""

    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.database = database

    async def record(
        self,
        *,
        company_id: str,
        actor_id: str | None,
        ip_address: str | None,
        module: str,
        action: str,
        entity_type: str,
        entity_id: str | None,
        old_value: Any,
        new_value: Any,
        level: str,
        outcome: str,
        message: str,
        request_id: str | None,
    ) -> None:
        if not ObjectId.is_valid(company_id):
            return
        document = {
            "company_id": ObjectId(company_id),
            "module": module,
            "action": action,
            "entity_type": entity_type,
            "old_value": sanitize_audit_value(old_value),
            "new_value": sanitize_audit_value(new_value),
            "level": level,
            "outcome": outcome,
            "message": message,
            "request_id": request_id,
            "occurred_at": datetime.now(UTC),
        }
        if actor_id and ObjectId.is_valid(actor_id):
            document["actor_id"] = ObjectId(actor_id)
        if ip_address:
            document["ip_address"] = ip_address
        if entity_id:
            document["entity_id"] = entity_id
        try:
            await self.database.audit_logs.insert_one(document)
        except PyMongoError:
            logger.exception("Audit log persistence failed", extra={"request_id": request_id})

    async def list(self, company_id: str, filters: AuditLogFilters, pagination: PaginationParams) -> dict[str, Any]:
        try:
            company, query, timezone = await self._query(company_id, filters)
            total, documents = await self._list_documents(query, pagination)
            actors = await self._actors(company["_id"], [document.get("actor_id") for document in documents])
            rows = [self._public(document, actors.get(document.get("actor_id")), timezone, include_values=False) for document in documents]
            return Page.create(items=rows, total=total, pagination=pagination).model_dump(mode="python")
        except PyMongoError as exc:
            logger.exception("Database error while listing audit logs")
            raise DatabaseUnavailableError("Audit logs are temporarily unavailable. Please retry.") from exc

    async def timeline(self, company_id: str, filters: AuditLogFilters, limit: int) -> list[dict[str, Any]]:
        try:
            company, query, timezone = await self._query(company_id, filters)
            documents = await self.database.audit_logs.find(query).sort("occurred_at", DESCENDING).limit(limit).to_list(limit)
            actors = await self._actors(company["_id"], [document.get("actor_id") for document in documents])
            return [self._public(document, actors.get(document.get("actor_id")), timezone, include_values=False) for document in documents]
        except PyMongoError as exc:
            logger.exception("Database error while loading audit timeline")
            raise DatabaseUnavailableError("Audit timeline is temporarily unavailable. Please retry.") from exc

    async def get(self, company_id: str, audit_id: str) -> dict[str, Any]:
        if not ObjectId.is_valid(audit_id):
            raise NotFoundError("Audit log was not found.")
        try:
            company = await self._company(company_id)
            document = await self.database.audit_logs.find_one({"_id": ObjectId(audit_id), "company_id": company["_id"]})
            if not document:
                raise NotFoundError("Audit log was not found.")
            actors = await self._actors(company["_id"], [document.get("actor_id")])
            return self._public(document, actors.get(document.get("actor_id")), self._timezone(company))
        except PyMongoError as exc:
            logger.exception("Database error while reading audit log")
            raise DatabaseUnavailableError("Audit log data is temporarily unavailable. Please retry.") from exc

    async def _company(self, company_id: str) -> dict[str, Any]:
        if not ObjectId.is_valid(company_id):
            raise NotFoundError("Company was not found.")
        company = await self.database.companies.find_one({"_id": ObjectId(company_id), "status": "active"})
        if not company:
            raise NotFoundError("Company was not found or is inactive.")
        return company

    async def _query(self, company_id: str, filters: AuditLogFilters) -> tuple[dict[str, Any], dict[str, Any], ZoneInfo]:
        company = await self._company(company_id)
        timezone = self._timezone(company)
        today = datetime.now(UTC).astimezone(timezone).date()
        date_from = filters.date_from or today - timedelta(days=29)
        date_to = filters.date_to or today
        query: dict[str, Any] = {
            "company_id": company["_id"],
            "occurred_at": {
                "$gte": datetime.combine(date_from, time.min, tzinfo=timezone).astimezone(UTC),
                "$lt": datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone).astimezone(UTC),
            },
        }
        if filters.module:
            query["module"] = filters.module
        if filters.action:
            query["action"] = filters.action
        if filters.level:
            query["level"] = filters.level
        if filters.user_id:
            query["actor_id"] = ObjectId(filters.user_id)
        if filters.search:
            pattern = {"$regex": re.escape(filters.search), "$options": "i"}
            query["$or"] = [{"module": pattern}, {"action": pattern}, {"entity_type": pattern}, {"message": pattern}, {"ip_address": pattern}]
        return company, query, timezone

    async def _list_documents(self, query: dict[str, Any], pagination: PaginationParams) -> tuple[int, list[dict[str, Any]]]:
        total, documents = await asyncio.gather(
            self.database.audit_logs.count_documents(query),
            self.database.audit_logs.find(query).sort("occurred_at", DESCENDING).skip(pagination.offset).limit(pagination.limit).to_list(pagination.limit),
        )
        return total, documents

    @staticmethod
    def _timezone(company: dict[str, Any]) -> ZoneInfo:
        try:
            return ZoneInfo(company.get("timezone", "Asia/Kolkata"))
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")

    async def _actors(self, company_id: ObjectId, actor_ids: list[ObjectId | None]) -> dict[ObjectId, dict[str, str | None]]:
        ids = list({actor_id for actor_id in actor_ids if actor_id})
        if not ids:
            return {}
        users = await self.database.users.find({"_id": {"$in": ids}, "company_id": company_id}).to_list(None)
        return {
            user["_id"]: {
                "id": str(user["_id"]),
                "name": user.get("display_name") or user.get("name") or user.get("username") or user.get("email", "Unknown user"),
                "email": user.get("email"),
            }
            for user in users
        }

    @staticmethod
    def _public(document: dict[str, Any], actor: dict[str, str | None] | None, timezone: ZoneInfo, *, include_values: bool = True) -> dict[str, Any]:
        occurred_at = document["occurred_at"]
        local = occurred_at.astimezone(timezone)
        output = {
            "id": str(document["_id"]),
            "actor": actor or {"id": None, "name": "System", "email": None},
            "ip_address": document.get("ip_address"),
            "module": document["module"],
            "action": document["action"],
            "entity_type": document["entity_type"],
            "entity_id": document.get("entity_id"),
            "level": document.get("level", "success"),
            "outcome": document.get("outcome", "success"),
            "message": document.get("message", "Activity recorded."),
            "request_id": document.get("request_id"),
            "occurred_at": occurred_at,
            "date": local.date(),
            "time": local.strftime("%H:%M:%S"),
        }
        if include_values:
            output["old_value"] = document.get("old_value")
            output["new_value"] = document.get("new_value")
        return output
