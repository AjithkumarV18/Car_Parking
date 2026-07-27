from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import CollectionInvalid


async def initialize_employee_collections(database: AsyncIOMotorDatabase) -> None:
    """Create employee collection validation and query indexes."""

    try:
        await database.create_collection(
            "employees",
            validator={
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": [
                        "company_id",
                        "user_id",
                        "employee_id",
                        "name",
                        "gender",
                        "email",
                        "phone",
                        "designation",
                        "role_id",
                        "salary",
                        "joining_date",
                        "status",
                    ],
                }
            },
            validationLevel="strict",
            validationAction="error",
        )
    except CollectionInvalid:
        pass
    await database.employees.create_indexes(
        [
            IndexModel([("company_id", ASCENDING), ("employee_id", ASCENDING)], unique=True, name="uq_employee_id"),
            IndexModel([("company_id", ASCENDING), ("email", ASCENDING)], unique=True, name="uq_employee_email"),
            IndexModel([("company_id", ASCENDING), ("status", ASCENDING), ("name", ASCENDING)], name="ix_employee_list"),
            IndexModel([("company_id", ASCENDING), ("parking_location_id", ASCENDING), ("status", ASCENDING)], name="ix_employee_location"),
            IndexModel([("company_id", ASCENDING), ("role_id", ASCENDING), ("status", ASCENDING)], name="ix_employee_role"),
            IndexModel([("company_id", ASCENDING), ("joining_date", DESCENDING)], name="ix_employee_joining"),
        ]
    )
