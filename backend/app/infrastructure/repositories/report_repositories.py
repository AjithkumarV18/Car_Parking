from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import CollectionInvalid


async def _create_collection_if_missing(database: AsyncIOMotorDatabase, name: str, validator: dict) -> None:
    try:
        await database.create_collection(name, validator=validator, validationLevel="strict", validationAction="error")
    except CollectionInvalid:
        pass


async def initialize_report_collections(database: AsyncIOMotorDatabase) -> None:
    """Provision future-facing audit and cancellation sources consumed by reports."""

    await _create_collection_if_missing(
        database,
        "audit_logs",
        {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["company_id", "occurred_at", "module", "action", "entity_type", "level", "outcome"],
                "properties": {
                    "company_id": {"bsonType": "objectId"},
                    "occurred_at": {"bsonType": "date"},
                    "actor_id": {"bsonType": ["objectId", "null"]},
                    "ip_address": {"bsonType": ["string", "null"]},
                    "module": {"bsonType": "string"},
                    "action": {"bsonType": "string"},
                    "entity_type": {"bsonType": "string"},
                    "entity_id": {"bsonType": ["objectId", "string", "null"]},
                    "old_value": {"bsonType": ["object", "array", "string", "null"]},
                    "new_value": {"bsonType": ["object", "array", "string", "null"]},
                    "level": {"enum": ["success", "warning", "error"]},
                    "outcome": {"enum": ["success", "failure"]},
                    "details": {"bsonType": "string"},
                    "message": {"bsonType": "string"},
                    "request_id": {"bsonType": ["string", "null"]},
                },
            }
        },
    )
    await _create_collection_if_missing(
        database,
        "cancelled_receipts",
        {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["company_id", "receipt_type", "cancelled_at", "status"],
                "properties": {
                    "company_id": {"bsonType": "objectId"},
                    "receipt_type": {"enum": ["entry", "exit"]},
                    "receipt_number": {"bsonType": "string"},
                    "vehicle_number": {"bsonType": "string"},
                    "token_number": {"bsonType": "string"},
                    "vehicle_type": {"enum": ["cycle", "bike", "car", "auto", "mini_bus", "bus", "truck"]},
                    "cancelled_at": {"bsonType": "date"},
                    "cancelled_by": {"bsonType": "objectId"},
                    "reason": {"bsonType": "string"},
                    "amount": {"bsonType": "decimal", "minimum": 0},
                    "status": {"enum": ["cancelled"]},
                },
            }
        },
    )
    await database.audit_logs.create_indexes(
        [
            IndexModel([("company_id", ASCENDING), ("occurred_at", DESCENDING)], name="ix_audit_company_time"),
            IndexModel([("company_id", ASCENDING), ("actor_id", ASCENDING), ("occurred_at", DESCENDING)], name="ix_audit_actor_time"),
            IndexModel([("company_id", ASCENDING), ("module", ASCENDING), ("occurred_at", DESCENDING)], name="ix_audit_module_time"),
            IndexModel([("company_id", ASCENDING), ("level", ASCENDING), ("occurred_at", DESCENDING)], name="ix_audit_level_time"),
        ]
    )
    await database.cancelled_receipts.create_indexes(
        [
            IndexModel([("company_id", ASCENDING), ("cancelled_at", DESCENDING)], name="ix_cancelled_receipt_time"),
            IndexModel([("company_id", ASCENDING), ("vehicle_number", ASCENDING)], name="ix_cancelled_receipt_vehicle"),
        ]
    )
