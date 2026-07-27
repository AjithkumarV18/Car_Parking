from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, IndexModel
from pymongo.errors import CollectionInvalid

from app.core.software_settings import SOFTWARE_FEATURE_DEFAULTS


async def initialize_settings_collections(database: AsyncIOMotorDatabase) -> None:
    """Create the tenant-scoped software feature settings collection."""

    try:
        await database.create_collection(
            "software_settings",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["company_id", "created_at", "updated_at", *SOFTWARE_FEATURE_DEFAULTS],
                    "properties": {
                        "company_id": {"bsonType": "objectId"},
                        **{key: {"bsonType": "bool"} for key in SOFTWARE_FEATURE_DEFAULTS},
                        "created_at": {"bsonType": "date"},
                        "updated_at": {"bsonType": "date"},
                        "updated_by": {"bsonType": ["objectId", "null"]},
                    },
                }
            },
            validationLevel="strict",
            validationAction="error",
        )
    except CollectionInvalid:
        pass
    await database.software_settings.create_indexes(
        [IndexModel([("company_id", ASCENDING)], unique=True, name="uq_software_settings_company")]
    )
