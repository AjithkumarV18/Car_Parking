from datetime import UTC, date, datetime

import pytest
from bson import ObjectId
from bson.decimal128 import Decimal128
from pydantic import ValidationError

from app.api.v1.schemas.audit import AuditLogFilters, AuditLogResponse
from app.application.audit.service import sanitize_audit_value
from app.core.middleware import AuditMiddleware


def test_audit_value_sanitization_and_mutation_target_mapping() -> None:
    value = sanitize_audit_value(
        {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "password": "not-for-audit-storage",
            "salary": Decimal128("1000.00"),
            "changed_at": datetime(2026, 7, 27, tzinfo=UTC),
        }
    )
    assert "_id" not in value
    assert value["password"] == "[REDACTED]"
    assert value["salary"] == "1000.00"
    assert value["changed_at"] == "2026-07-27T00:00:00+00:00"
    assert AuditMiddleware._target("/api/v1/employees/507f1f77bcf86cd799439011", "PATCH") == {
        "module": "employee",
        "action": "update",
        "entity_type": "employee",
        "collection": "employees",
        "entity_id": "507f1f77bcf86cd799439011",
    }


def test_audit_contract_and_filter_validation() -> None:
    with pytest.raises(ValidationError, match="Date from must be on or before"):
        AuditLogFilters(date_from=date(2026, 7, 28), date_to=date(2026, 7, 27))

    log = AuditLogResponse(
        id="507f1f77bcf86cd799439011",
        actor={"id": "507f1f77bcf86cd799439012", "name": "Maya Singh", "email": "maya@example.com"},
        ip_address="127.0.0.1",
        module="employee",
        action="update",
        entity_type="employee",
        entity_id="507f1f77bcf86cd799439013",
        old_value={"designation": "Operator"},
        new_value={"designation": "Supervisor"},
        level="success",
        outcome="success",
        message="Employee update completed.",
        request_id="request-1",
        occurred_at=datetime(2026, 7, 27, 10, 0, tzinfo=UTC),
        date=date(2026, 7, 27),
        time="15:30:00",
    )
    assert log.new_value == {"designation": "Supervisor"}
