"""Mongo-backed API tests; skipped unless an isolated test database is explicitly enabled."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_login_and_authorized_advanced_request_against_mongodb() -> None:
    if os.environ.get("RUN_INTEGRATION_TESTS") != "1":
        pytest.skip("Set RUN_INTEGRATION_TESTS=1 with an isolated MongoDB test database to run integration tests.")

    from app.application.auth.service import password_hasher
    from app.main import create_application

    application = create_application()
    async with application.router.lifespan_context(application):
        database = application.state.mongo.database
        if not database.name.endswith("_test"):
            pytest.fail("Integration tests require a database name ending in '_test'.")
        collections = (
            "users",
            "auth_sessions",
            "password_reset_tokens",
            "companies",
            "branches",
            "parking_locations",
            "monthly_passes",
            "parking_slots",
            "reserved_slots",
        )
        for collection in collections:
            await database[collection].delete_many({})
        now = datetime.now(UTC)
        company_id = ObjectId()
        await database.companies.insert_one(
            {
                "_id": company_id,
                "company_name": "Integration Tenant",
                "code": "INTEGRATION",
                "currency": "INR",
                "status": "active",
                "created_at": now,
                "updated_at": now,
            }
        )
        admin_role = await database.roles.find_one({"scope": "system", "code": "admin", "status": "active"})
        assert admin_role is not None
        await database.users.insert_one(
            {
                "company_id": company_id,
                "email": "admin@integration.test",
                "password_hash": password_hasher.hash("IntegrationPassword1!"),
                "display_name": "Integration Admin",
                "status": "active",
                "role_ids": [admin_role["_id"]],
                "is_super_admin": False,
                "created_at": now,
                "updated_at": now,
            }
        )
        headers = {"X-Company-ID": str(company_id)}
        async with AsyncClient(transport=ASGITransport(app=application), base_url="http://testserver") as client:
            health = await client.get("/api/v1/system/health")
            login = await client.post(
                "/api/v1/auth/login",
                headers=headers,
                json={"email": "admin@integration.test", "password": "IntegrationPassword1!", "remember_me": False},
            )
            token = login.json()["data"]["access_token"]
            advanced = await client.get(
                "/api/v1/advanced/parking-locations",
                headers={**headers, "Authorization": f"Bearer {token}"},
            )

    assert health.status_code == 200
    assert login.status_code == 200
    assert advanced.status_code == 200
    assert advanced.json()["data"] == []
