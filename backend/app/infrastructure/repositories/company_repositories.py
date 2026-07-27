from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, IndexModel
from pymongo.errors import CollectionInvalid


async def _create_collection_if_missing(
    database: AsyncIOMotorDatabase,
    name: str,
    required: list[str],
) -> None:
    try:
        await database.create_collection(
            name,
            validator={"$jsonSchema": {"bsonType": "object", "required": required}},
            validationLevel="strict",
            validationAction="error",
        )
    except CollectionInvalid:
        pass


async def initialize_company_collections(database: AsyncIOMotorDatabase) -> None:
    """Create company-management collections and the indexes used by CRUD queries."""

    await _create_collection_if_missing(
        database,
        "companies",
        ["company_name", "code", "currency", "status", "created_at", "updated_at"],
    )
    await _create_collection_if_missing(
        database,
        "branches",
        ["company_id", "name", "code", "status", "created_at", "updated_at"],
    )
    await _create_collection_if_missing(
        database,
        "parking_locations",
        ["company_id", "branch_id", "name", "code", "status", "created_at", "updated_at"],
    )
    await database.companies.create_indexes(
        [
            IndexModel([("code", ASCENDING)], unique=True, name="uq_company_code"),
            IndexModel([("company_name", ASCENDING)], name="ix_company_name"),
            IndexModel([("status", ASCENDING), ("company_name", ASCENDING)], name="ix_company_status_name"),
        ]
    )
    await database.branches.create_indexes(
        [
            IndexModel(
                [("company_id", ASCENDING), ("code", ASCENDING)],
                unique=True,
                name="uq_branch_company_code",
            ),
            IndexModel(
                [("company_id", ASCENDING), ("status", ASCENDING), ("name", ASCENDING)],
                name="ix_branch_company_status_name",
            ),
        ]
    )
    await database.parking_locations.create_indexes(
        [
            IndexModel(
                [("branch_id", ASCENDING), ("code", ASCENDING)],
                unique=True,
                name="uq_location_branch_code",
            ),
            IndexModel(
                [("company_id", ASCENDING), ("branch_id", ASCENDING), ("status", ASCENDING)],
                name="ix_location_scope_status",
            ),
            IndexModel([("geo", "2dsphere")], name="ix_location_geo", sparse=True),
        ]
    )
