"""Create or update a non-production demo tenant with sample parking data."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime

from bson.decimal128 import Decimal128
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.application.auth.service import password_hasher
from app.application.system.seed import SeedCredentials, validate_seed_credentials
from app.core.config import get_settings
from app.infrastructure.database.mongodb import MongoConnection
from app.infrastructure.repositories.advanced_repositories import initialize_advanced_collections
from app.infrastructure.repositories.auth_repositories import initialize_auth_collections
from app.infrastructure.repositories.company_repositories import initialize_company_collections
from app.infrastructure.repositories.employee_repositories import initialize_employee_collections
from app.infrastructure.repositories.parking_repositories import initialize_parking_collections
from app.infrastructure.repositories.rate_repositories import initialize_rate_collections
from app.infrastructure.repositories.report_repositories import initialize_report_collections
from app.infrastructure.repositories.settings_repositories import initialize_settings_collections


async def initialize_database(database: AsyncIOMotorDatabase) -> None:
    await initialize_auth_collections(database)
    await initialize_company_collections(database)
    await initialize_employee_collections(database)
    await initialize_rate_collections(database)
    await initialize_parking_collections(database)
    await initialize_report_collections(database)
    await initialize_settings_collections(database)
    await initialize_advanced_collections(database)


async def upsert_demo_data(database: AsyncIOMotorDatabase, credentials: SeedCredentials) -> str:
    now = datetime.now(UTC)
    company = await database.companies.find_one_and_update(
        {"code": "DEMO"},
        {
            "$set": {
                "company_name": "Demo Commercial Parking",
                "code": "DEMO",
                "currency": "INR",
                "status": "active",
                "address": {
                    "line1": "100 Logistics Park",
                    "city": "Bengaluru",
                    "state": "Karnataka",
                    "postal_code": "560001",
                    "country_code": "IN",
                },
                "phone": "+919876543210",
                "email": "operations@demo.parking",
                "theme": {"primary_color": "#0B4F6C", "secondary_color": "#EF8354"},
                "date_format": "DD/MM/YYYY",
                "time_format": "24h",
                "timezone": "Asia/Kolkata",
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    branch = await database.branches.find_one_and_update(
        {"company_id": company["_id"], "code": "MAIN"},
        {
            "$set": {
                "company_id": company["_id"],
                "name": "Main Branch",
                "code": "MAIN",
                "status": "active",
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    location = await database.parking_locations.find_one_and_update(
        {"branch_id": branch["_id"], "code": "YARD-1"},
        {
            "$set": {
                "company_id": company["_id"],
                "branch_id": branch["_id"],
                "name": "North Yard",
                "code": "YARD-1",
                "capacity": 48,
                "status": "active",
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    effective_date = datetime(2026, 1, 1, tzinfo=UTC)
    for vehicle_type, first_amount, second_amount in (
        ("bike", "20.00", "50.00"),
        ("car", "40.00", "100.00"),
        ("truck", "120.00", "350.00"),
    ):
        rate = {
            "company_id": company["_id"],
            "vehicle_type": vehicle_type,
            "effective_date": effective_date,
            "duration_slabs": [
                {"from_minutes": 0, "to_minutes": 60, "amount": Decimal128(first_amount), "gst_percent": Decimal128("18.00")},
                {"from_minutes": 60, "to_minutes": None, "amount": Decimal128(second_amount), "gst_percent": Decimal128("18.00")},
            ],
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        await database.parking_rates.update_one(
            {"company_id": company["_id"], "vehicle_type": vehicle_type, "effective_date": effective_date},
            {"$setOnInsert": rate},
            upsert=True,
        )
    for number in range(1, 13):
        slot_number = f"A-{number:02d}"
        await database.parking_slots.update_one(
            {"company_id": company["_id"], "parking_location_id": location["_id"], "slot_number": slot_number},
            {
                "$setOnInsert": {
                    "company_id": company["_id"],
                    "parking_location_id": location["_id"],
                    "slot_number": slot_number,
                    "vehicle_type": "car",
                    "status": "available",
                    "created_by": company["_id"],
                }
            },
            upsert=True,
        )
    monthly_pass = {
        "company_id": company["_id"],
        "pass_number": "MP-DEMO-00001",
        "vehicle_number": "KA01DEMO01",
        "vehicle_type": "car",
        "holder_name": "Demo Fleet",
        "parking_location_id": location["_id"],
        "valid_from": effective_date,
        "valid_until": datetime(2026, 12, 31, tzinfo=UTC),
        "amount": Decimal128("2500.00"),
        "status": "active",
        "created_at": now,
        "created_by": company["_id"],
    }
    await database.monthly_passes.update_one(
        {"company_id": company["_id"], "pass_number": "MP-DEMO-00001"},
        {"$setOnInsert": monthly_pass},
        upsert=True,
    )
    roles = {
        role["code"]: role
        async for role in database.roles.find(
            {"scope": "system", "code": {"$in": ["admin", "super_admin"]}, "status": "active"}
        )
    }
    for email, password, display_name, role_code, is_super_admin in (
        (credentials.admin_email, credentials.admin_password, "Demo Administrator", "admin", False),
        (credentials.super_admin_email, credentials.super_admin_password, "Demo Super Administrator", "super_admin", True),
    ):
        await database.users.update_one(
            {"email": email.lower().strip()},
            {
                "$set": {
                    "company_id": company["_id"],
                    "display_name": display_name,
                    "status": "active",
                    "role_ids": [roles[role_code]["_id"]],
                    "is_super_admin": is_super_admin,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "email": email.lower().strip(),
                    "password_hash": password_hasher.hash(password),
                    "created_at": now,
                },
            },
            upsert=True,
        )
    return str(company["_id"])


async def main() -> None:
    settings = get_settings()
    credentials = SeedCredentials(
        admin_email=os.environ.get("SEED_ADMIN_EMAIL", "admin@demo.parking"),
        admin_password=os.environ.get("SEED_ADMIN_PASSWORD", ""),
        super_admin_email=os.environ.get("SEED_SUPER_ADMIN_EMAIL", "superadmin@demo.parking"),
        super_admin_password=os.environ.get("SEED_SUPER_ADMIN_PASSWORD", ""),
    )
    validate_seed_credentials(credentials, is_production=settings.is_production)
    connection = MongoConnection(settings)
    await connection.connect()
    try:
        await initialize_database(connection.database)
        company_id = await upsert_demo_data(connection.database, credentials)
    finally:
        await connection.close()
    print(f"Demo tenant seeded. X-Company-ID: {company_id}")
    print(f"Admin: {credentials.admin_email}")
    print(f"Super admin: {credentials.super_admin_email}")


if __name__ == "__main__":
    asyncio.run(main())
