from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import CollectionInvalid


async def _create_collection_if_missing(database: AsyncIOMotorDatabase, name: str, validator: dict) -> None:
    try:
        await database.create_collection(
            name,
            validator=validator,
            validationLevel="strict",
            validationAction="error",
        )
    except CollectionInvalid:
        pass


async def initialize_parking_collections(database: AsyncIOMotorDatabase) -> None:
    """Create operational parking collections, strict validators, and safety indexes."""

    await _create_collection_if_missing(
        database,
        "vehicle_entries",
        {
            "$jsonSchema": {
                "bsonType": "object",
                "required": [
                    "company_id", "vehicle_number", "vehicle_type", "entry_at", "parking_number", "token_number",
                    "advance_amount", "rate_snapshot", "entry_by", "status",
                ],
                "properties": {
                    "company_id": {"bsonType": "objectId"},
                    "vehicle_number": {"bsonType": "string", "pattern": "^[A-Z0-9]{4,20}$"},
                    "vehicle_type": {"enum": ["cycle", "bike", "car", "auto", "mini_bus", "bus", "truck"]},
                    "entry_at": {"bsonType": "date"},
                    "parking_number": {"bsonType": "string"},
                    "token_number": {"bsonType": "string"},
                    "advance_amount": {"bsonType": "decimal", "minimum": 0},
                    "rate_snapshot": {"bsonType": "object"},
                    "entry_by": {"bsonType": "objectId"},
                    "status": {"enum": ["open", "closed"]},
                },
            }
        },
    )
    await _create_collection_if_missing(
        database,
        "vehicle_exits",
        {
            "$jsonSchema": {
                "bsonType": "object",
                "required": [
                    "company_id", "entry_id", "token_number", "exit_at", "exit_by", "duration_minutes",
                    "parking_charge", "gst_percent", "gst_amount", "total_amount", "advance_amount",
                    "advance_applied", "paid_amount", "balance_amount", "status",
                ],
                "properties": {
                    "company_id": {"bsonType": "objectId"},
                    "entry_id": {"bsonType": "objectId"},
                    "exit_at": {"bsonType": "date"},
                    "exit_by": {"bsonType": "objectId"},
                    "duration_minutes": {"bsonType": "int", "minimum": 0},
                    "parking_charge": {"bsonType": "decimal", "minimum": 0},
                    "gst_amount": {"bsonType": "decimal", "minimum": 0},
                    "total_amount": {"bsonType": "decimal", "minimum": 0},
                    "advance_amount": {"bsonType": "decimal", "minimum": 0},
                    "advance_applied": {"bsonType": "decimal", "minimum": 0},
                    "paid_amount": {"bsonType": "decimal", "minimum": 0},
                    "balance_amount": {"bsonType": "decimal", "minimum": 0},
                    "status": {"enum": ["completed"]},
                },
            }
        },
    )
    await _create_collection_if_missing(
        database,
        "payments",
        {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["company_id", "reference_type", "reference_id", "amount", "method", "status", "paid_at"],
                "properties": {
                    "company_id": {"bsonType": "objectId"},
                    "reference_id": {"bsonType": "objectId"},
                    "amount": {"bsonType": "decimal", "minimum": 0},
                    "method": {"enum": ["cash", "upi", "card"]},
                    "status": {"enum": ["paid"]},
                },
            }
        },
    )
    await _create_collection_if_missing(
        database,
        "parking_counters",
        {"$jsonSchema": {"bsonType": "object", "required": ["key", "sequence", "company_id", "updated_at"]}},
    )

    await database.vehicle_entries.create_indexes(
        [
            IndexModel([("company_id", ASCENDING), ("parking_number", ASCENDING)], unique=True, name="uq_entry_parking_number"),
            IndexModel([("company_id", ASCENDING), ("token_number", ASCENDING)], unique=True, name="uq_entry_token_number"),
            IndexModel(
                [("company_id", ASCENDING), ("vehicle_number", ASCENDING)],
                unique=True,
                partialFilterExpression={"status": "open"},
                name="uq_open_entry_vehicle",
            ),
            IndexModel([("company_id", ASCENDING), ("status", ASCENDING), ("entry_at", DESCENDING)], name="ix_entry_operations"),
            IndexModel([("company_id", ASCENDING), ("entry_at", DESCENDING)], name="ix_entry_reporting"),
            IndexModel([("company_id", ASCENDING), ("rfid", ASCENDING), ("status", ASCENDING)], name="ix_entry_rfid"),
            IndexModel([("company_id", ASCENDING), ("qr_code", ASCENDING), ("status", ASCENDING)], name="ix_entry_qr"),
        ]
    )
    await database.vehicle_exits.create_indexes(
        [
            IndexModel([("entry_id", ASCENDING)], unique=True, name="uq_exit_entry"),
            IndexModel([("company_id", ASCENDING), ("exit_at", DESCENDING)], name="ix_exit_operations"),
            IndexModel([("company_id", ASCENDING), ("status", ASCENDING), ("exit_at", DESCENDING)], name="ix_exit_reporting"),
            IndexModel([("company_id", ASCENDING), ("exit_by", ASCENDING), ("exit_at", DESCENDING)], name="ix_exit_employee_reporting"),
            IndexModel([("company_id", ASCENDING), ("token_number", ASCENDING)], name="ix_exit_token"),
        ]
    )
    await database.payments.create_indexes(
        [
            IndexModel([("company_id", ASCENDING), ("idempotency_key", ASCENDING)], unique=True, name="uq_payment_idempotency"),
            IndexModel([("company_id", ASCENDING), ("reference_type", ASCENDING), ("reference_id", ASCENDING)], name="ix_payment_reference"),
            IndexModel([("company_id", ASCENDING), ("status", ASCENDING), ("paid_at", DESCENDING)], name="ix_payment_reporting"),
        ]
    )
    await database.parking_counters.create_index([("key", ASCENDING)], unique=True, name="uq_parking_counter_key")
