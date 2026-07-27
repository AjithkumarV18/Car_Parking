from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.core.exceptions import NotFoundError
from app.core.software_settings import SOFTWARE_FEATURE_DEFAULTS


class SoftwareSettingsService:
    """Stores feature flags independently for every active company."""

    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.database = database

    async def _company(self, company_id: str) -> ObjectId:
        if not ObjectId.is_valid(company_id):
            raise NotFoundError("Company was not found.")
        identifier = ObjectId(company_id)
        if not await self.database.companies.find_one({"_id": identifier, "status": "active"}):
            raise NotFoundError("Company was not found or is inactive.")
        return identifier

    @staticmethod
    def _public(document: dict[str, Any] | None) -> dict[str, bool]:
        return {key: bool((document or {}).get(key, default)) for key, default in SOFTWARE_FEATURE_DEFAULTS.items()}

    async def get(self, company_id: str) -> dict[str, bool]:
        company = await self._company(company_id)
        return self._public(await self.database.software_settings.find_one({"company_id": company}))

    async def update(self, company_id: str, payload: dict[str, bool], actor_id: str) -> dict[str, bool]:
        company = await self._company(company_id)
        now = datetime.now(UTC)
        initial_features = {key: value for key, value in SOFTWARE_FEATURE_DEFAULTS.items() if key not in payload}
        document = await self.database.software_settings.find_one_and_update(
            {"company_id": company},
            {
                "$set": {**payload, "updated_at": now, "updated_by": ObjectId(actor_id)},
                "$setOnInsert": {"company_id": company, **initial_features, "created_at": now},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return self._public(document)
