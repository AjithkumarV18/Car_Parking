from __future__ import annotations

from datetime import UTC, datetime

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


async def initialize_auth_collections(database: AsyncIOMotorDatabase) -> None:
    """Create authentication collections, validators, seed RBAC defaults, and indexes."""

    await _create_collection_if_missing(
        database,
        "users",
        ["company_id", "email", "password_hash", "display_name", "status", "role_ids"],
    )
    await _create_collection_if_missing(
        database,
        "auth_sessions",
        ["user_id", "company_id", "token_hash", "expires_at", "status"],
    )
    await _create_collection_if_missing(
        database,
        "password_reset_tokens",
        ["user_id", "company_id", "token_hash", "expires_at", "used_at"],
    )
    await _create_collection_if_missing(database, "roles", ["scope", "code", "permission_ids", "status"])
    await _create_collection_if_missing(database, "permissions", ["key", "name", "status"])

    await database.users.create_indexes(
        [
            IndexModel([("email", ASCENDING)], unique=True, name="uq_users_email"),
            IndexModel([("username", ASCENDING)], unique=True, sparse=True, name="uq_users_username"),
            IndexModel([("company_id", ASCENDING), ("status", ASCENDING)], name="ix_users_tenant_status"),
        ]
    )
    await database.auth_sessions.create_indexes(
        [
            IndexModel([("session_id", ASCENDING)], unique=True, name="uq_session_id"),
            IndexModel([("user_id", ASCENDING), ("status", ASCENDING)], name="ix_user_sessions"),
            IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0, name="ttl_expired_sessions"),
        ]
    )
    await database.password_reset_tokens.create_indexes(
        [
            IndexModel([("token_hash", ASCENDING)], unique=True, name="uq_reset_token_hash"),
            IndexModel([("user_id", ASCENDING), ("used_at", ASCENDING)], name="ix_user_reset_tokens"),
            IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0, name="ttl_expired_reset_tokens"),
        ]
    )
    await database.roles.create_indexes(
        [
            IndexModel(
                [("scope", ASCENDING), ("company_id", ASCENDING), ("code", ASCENDING)],
                unique=True,
                name="uq_role_scope_code",
            )
        ]
    )
    await database.permissions.create_index([("key", ASCENDING)], unique=True, name="uq_permission_key")

    now = datetime.now(UTC)
    permission_specs = [
        {"key": "system:read", "name": "Read system information", "module": "system", "action": "read"},
        {"key": "auth:self_read", "name": "Read own authentication profile", "module": "auth", "action": "details"},
        {"key": "dashboard:show", "name": "Show dashboard", "module": "dashboard", "action": "show"},
        {"key": "report:show", "name": "Show reports", "module": "report", "action": "show"},
        {"key": "report:details", "name": "Export reports", "module": "report", "action": "details"},
        {"key": "audit:show", "name": "Show audit logs", "module": "audit", "action": "show"},
        {"key": "audit:details", "name": "View audit log details", "module": "audit", "action": "details"},
        {"key": "advanced:show", "name": "Show advanced parking menu", "module": "advanced", "action": "show"},
        {"key": "advanced:manage", "name": "Manage passes, slots, and reservations", "module": "advanced", "action": "save"},
        {"key": "company:show", "name": "Show company menu", "module": "company", "action": "show"},
        {"key": "company:save", "name": "Create companies", "module": "company", "action": "save"},
        {"key": "company:edit", "name": "Edit companies", "module": "company", "action": "edit"},
        {"key": "company:delete", "name": "Deactivate companies", "module": "company", "action": "delete"},
        {"key": "company:details", "name": "View company details", "module": "company", "action": "details"},
        {"key": "role:show", "name": "Show role menu", "module": "role", "action": "show"},
        {"key": "role:save", "name": "Create roles", "module": "role", "action": "save"},
        {"key": "role:edit", "name": "Edit roles", "module": "role", "action": "edit"},
        {"key": "role:delete", "name": "Delete roles", "module": "role", "action": "delete"},
        {"key": "role:details", "name": "View role details", "module": "role", "action": "details"},
        {"key": "employee:show", "name": "Show employee menu", "module": "employee", "action": "show"},
        {"key": "employee:save", "name": "Create employees", "module": "employee", "action": "save"},
        {"key": "employee:edit", "name": "Edit employees", "module": "employee", "action": "edit"},
        {"key": "employee:delete", "name": "Deactivate employees", "module": "employee", "action": "delete"},
        {"key": "employee:details", "name": "View employee details and exports", "module": "employee", "action": "details"},
        {"key": "rate:show", "name": "Show parking rate menu", "module": "rate", "action": "show"},
        {"key": "rate:save", "name": "Create parking rates", "module": "rate", "action": "save"},
        {"key": "rate:edit", "name": "Edit parking rates", "module": "rate", "action": "edit"},
        {"key": "rate:delete", "name": "Deactivate parking rates", "module": "rate", "action": "delete"},
        {"key": "rate:details", "name": "View parking rate details", "module": "rate", "action": "details"},
        {"key": "parking_entry:show", "name": "Show vehicle entry screen", "module": "parking_entry", "action": "show"},
        {"key": "parking_entry:save", "name": "Create vehicle entries", "module": "parking_entry", "action": "save"},
        {"key": "parking_entry:details", "name": "View and print entry receipts", "module": "parking_entry", "action": "details"},
        {"key": "parking_exit:show", "name": "Show vehicle exit screen", "module": "parking_exit", "action": "show"},
        {"key": "parking_exit:save", "name": "Complete vehicle exits", "module": "parking_exit", "action": "save"},
        {"key": "parking_exit:details", "name": "View and print exit receipts", "module": "parking_exit", "action": "details"},
    ]
    for spec in permission_specs:
        await database.permissions.update_one(
            {"key": spec["key"]},
            {"$setOnInsert": {**spec, "status": "active", "created_at": now, "updated_at": now}},
            upsert=True,
        )
    permission_map = {
        document["key"]: document["_id"]
        async for document in database.permissions.find({"key": {"$in": [spec["key"] for spec in permission_specs]}})
    }
    role_specs = [
        ("viewer", "Viewer", ["auth:self_read", "dashboard:show"]),
        ("super_admin", "Super Admin", [spec["key"] for spec in permission_specs]),
        (
            "admin",
            "Admin",
            [
                "dashboard:show",
                "report:show",
                "report:details",
                "audit:show",
                "audit:details",
                "advanced:show",
                "advanced:manage",
                "company:show",
                "company:details",
                "employee:show",
                "employee:save",
                "employee:edit",
                "employee:delete",
                "employee:details",
                "rate:show",
                "rate:save",
                "rate:edit",
                "rate:delete",
                "rate:details",
                "parking_entry:show",
                "parking_entry:save",
                "parking_entry:details",
                "parking_exit:show",
                "parking_exit:save",
                "parking_exit:details",
            ],
        ),
        (
            "owner",
            "Owner",
            ["dashboard:show", "report:show", "report:details", "company:show", "company:details", "advanced:show"],
        ),
        (
            "employee",
            "Employee",
            [
                "dashboard:show",
                "parking_entry:show",
                "parking_entry:save",
                "parking_entry:details",
                "parking_exit:show",
                "parking_exit:save",
                "parking_exit:details",
            ],
        ),
    ]
    for code, name, keys in role_specs:
        await database.roles.update_one(
        {"scope": "system", "company_id": None, "code": code},
        {
            "$setOnInsert": {
                "scope": "system",
                "company_id": None,
                "code": code,
                "name": name,
                "is_system": True,
                "status": "active",
                "created_at": now,
            },
            "$set": {
                "permission_ids": [
                    permission_map[key]
                    for key in keys
                    if key in permission_map
                ],
                "updated_at": now,
            },
        },
        upsert=True,
    )
