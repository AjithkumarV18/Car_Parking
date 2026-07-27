from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId, json_util
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from app.core.exceptions import DatabaseUnavailableError, InvalidBackupError, NotFoundError


class TenantBackupService:
    """Export and merge-restore one tenant without touching authentication data."""

    collections = (
        "companies",
        "branches",
        "parking_locations",
        "employees",
        "parking_rates",
        "vehicle_entries",
        "vehicle_exits",
        "payments",
        "monthly_passes",
        "parking_slots",
        "reserved_slots",
        "audit_logs",
        "settings",
    )

    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.database = database

    async def export(self, company_id: str) -> str:
        company = await self._company(company_id)
        documents: dict[str, list[dict[str, Any]]] = {}
        try:
            for name in self.collections:
                criteria = {"_id": company} if name == "companies" else {"company_id": company}
                documents[name] = await self.database[name].find(criteria).to_list(None)
        except PyMongoError as exc:
            raise DatabaseUnavailableError("Unable to create the company backup.") from exc
        return json_util.dumps(
            {
                "schema_version": 1,
                "generated_at": datetime.now(UTC),
                "company_id": company,
                "collections": documents,
            },
            indent=2,
        )

    async def restore(self, company_id: str, backup_json: str) -> dict[str, int]:
        company = await self._company(company_id)
        try:
            backup = json_util.loads(backup_json)
        except (TypeError, ValueError) as exc:
            raise InvalidBackupError("The uploaded file is not a valid MongoDB backup JSON document.") from exc
        if not isinstance(backup, dict) or backup.get("schema_version") != 1 or not isinstance(backup.get("collections"), dict):
            raise InvalidBackupError("The backup format or schema version is not supported.")
        if backup.get("company_id") != company:
            raise InvalidBackupError("The backup belongs to a different company.")

        collections = backup["collections"]
        validated: dict[str, list[dict[str, Any]]] = {}
        for name in self.collections:
            records = collections.get(name, [])
            if not isinstance(records, list):
                raise InvalidBackupError(f"Backup collection '{name}' must be an array.")
            for record in records:
                if not isinstance(record, dict) or not isinstance(record.get("_id"), ObjectId):
                    raise InvalidBackupError(f"Backup collection '{name}' contains an invalid record.")
                if name == "companies":
                    if record["_id"] != company:
                        raise InvalidBackupError("Company record does not match the selected company.")
                elif record.get("company_id") != company:
                    raise InvalidBackupError(f"Backup collection '{name}' contains another company's data.")
            validated[name] = records

        restored: dict[str, int] = {}
        try:
            for name in self.collections:
                records = validated[name]
                written = 0
                for record in records:
                    await self.database[name].replace_one({"_id": record["_id"]}, record, upsert=True)
                    written += 1
                restored[name] = written
        except PyMongoError as exc:
            raise DatabaseUnavailableError("The backup could not be restored because the database is unavailable.") from exc
        return restored

    async def _company(self, company_id: str) -> ObjectId:
        if not ObjectId.is_valid(company_id):
            raise NotFoundError("Company was not found.")
        company = ObjectId(company_id)
        if not await self.database.companies.find_one({"_id": company, "status": "active"}):
            raise NotFoundError("Company was not found or is inactive.")
        return company
