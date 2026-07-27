from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import CollectionInvalid

from app.shared.constants import PARKING_RATE_STATUSES, VEHICLE_TYPES


async def initialize_rate_collections(database: AsyncIOMotorDatabase) -> None:
    """Create the tenant-scoped parking-rate collection and its query indexes."""

    try:
        await database.create_collection(
            "parking_rates",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["company_id", "vehicle_type", "duration_slabs", "effective_date", "status"],
                    "properties": {
                        "company_id": {"bsonType": "objectId"},
                        "vehicle_type": {"enum": list(VEHICLE_TYPES)},
                        "duration_slabs": {
                            "bsonType": "array",
                            "minItems": 1,
                            "items": {
                                "bsonType": "object",
                                "required": ["from_minutes", "to_minutes", "amount", "gst_percent"],
                                "properties": {
                                    "from_minutes": {"bsonType": "int", "minimum": 0},
                                    "to_minutes": {"bsonType": ["int", "null"], "minimum": 0},
                                    "amount": {"bsonType": "decimal", "minimum": 0},
                                    "gst_percent": {"bsonType": "decimal", "minimum": 0, "maximum": 100},
                                },
                            },
                        },
                        "effective_date": {"bsonType": "date"},
                        "status": {"enum": list(PARKING_RATE_STATUSES)},
                    },
                }
            },
            validationLevel="strict",
            validationAction="error",
        )
    except CollectionInvalid:
        pass

    await database.parking_rates.create_indexes(
        [
            IndexModel(
                [("company_id", ASCENDING), ("vehicle_type", ASCENDING), ("effective_date", ASCENDING)],
                unique=True,
                name="uq_rate_vehicle_effective_date",
            ),
            IndexModel(
                [("company_id", ASCENDING), ("status", ASCENDING), ("vehicle_type", ASCENDING), ("effective_date", DESCENDING)],
                name="ix_rate_list",
            ),
            IndexModel([("company_id", ASCENDING), ("effective_date", DESCENDING)], name="ix_rate_effective_date"),
        ]
    )
