from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import CollectionInvalid


async def _create_collection_if_missing(database: AsyncIOMotorDatabase, name: str, validator: dict) -> None:
    try:
        await database.create_collection(name, validator=validator, validationLevel="strict", validationAction="error")
    except CollectionInvalid:
        pass


async def initialize_advanced_collections(database: AsyncIOMotorDatabase) -> None:
    """Create tenant-scoped advanced parking collections and indexes."""

    await _create_collection_if_missing(
        database,
        "monthly_passes",
        {
            "$jsonSchema": {
                "bsonType": "object",
                "required": [
                    "company_id", "pass_number", "vehicle_number", "vehicle_type", "holder_name", "valid_from",
                    "valid_until", "amount", "status", "created_at", "created_by",
                ],
                "properties": {
                    "company_id": {"bsonType": "objectId"}, "pass_number": {"bsonType": "string"},
                    "vehicle_number": {"bsonType": "string", "pattern": "^[A-Z0-9]{4,20}$"},
                    "vehicle_type": {"enum": ["cycle", "bike", "car", "auto", "mini_bus", "bus", "truck"]},
                    "valid_from": {"bsonType": "date"}, "valid_until": {"bsonType": "date"},
                    "amount": {"bsonType": "decimal", "minimum": 0}, "status": {"enum": ["active", "expired", "suspended"]},
                },
            }
        },
    )
    await _create_collection_if_missing(
        database,
        "parking_slots",
        {
            "$jsonSchema": {
                "bsonType": "object", "required": ["company_id", "parking_location_id", "slot_number", "status", "created_by"],
                "properties": {
                    "company_id": {"bsonType": "objectId"}, "parking_location_id": {"bsonType": "objectId"},
                    "slot_number": {"bsonType": "string"}, "status": {"enum": ["available", "occupied", "reserved", "maintenance"]},
                },
            }
        },
    )
    await _create_collection_if_missing(
        database,
        "reserved_slots",
        {
            "$jsonSchema": {
                "bsonType": "object",
                "required": [
                    "company_id", "parking_slot_id", "vehicle_number", "holder_name", "valid_from", "valid_until",
                    "status", "created_at", "created_by",
                ],
                "properties": {
                    "company_id": {"bsonType": "objectId"}, "parking_slot_id": {"bsonType": "objectId"},
                    "vehicle_number": {"bsonType": "string", "pattern": "^[A-Z0-9]{4,20}$"},
                    "valid_from": {"bsonType": "date"}, "valid_until": {"bsonType": "date"},
                    "status": {"enum": ["active", "cancelled", "completed"]},
                },
            }
        },
    )
    await database.monthly_passes.create_indexes([
        IndexModel([("company_id", ASCENDING), ("pass_number", ASCENDING)], unique=True, name="uq_monthly_pass_number"),
        IndexModel([("company_id", ASCENDING), ("vehicle_number", ASCENDING), ("status", ASCENDING)], name="ix_monthly_pass_vehicle"),
        IndexModel([("company_id", ASCENDING), ("valid_until", ASCENDING)], name="ix_monthly_pass_expiry"),
    ])
    await database.parking_slots.create_indexes([
        IndexModel(
            [("company_id", ASCENDING), ("parking_location_id", ASCENDING), ("slot_number", ASCENDING)],
            unique=True,
            name="uq_parking_slot_location_number",
        ),
        IndexModel([("company_id", ASCENDING), ("parking_location_id", ASCENDING), ("status", ASCENDING)], name="ix_parking_slot_map"),
    ])
    await database.reserved_slots.create_indexes([
        IndexModel(
            [("company_id", ASCENDING), ("parking_slot_id", ASCENDING), ("status", ASCENDING), ("valid_from", ASCENDING), ("valid_until", DESCENDING)],
            name="ix_reservation_overlap",
        ),
        IndexModel(
            [("company_id", ASCENDING), ("vehicle_number", ASCENDING), ("status", ASCENDING), ("valid_from", ASCENDING), ("valid_until", ASCENDING)],
            name="ix_reservation_vehicle_lookup",
        ),
        IndexModel([("company_id", ASCENDING), ("valid_until", ASCENDING)], name="ix_reservation_expiry"),
    ])
