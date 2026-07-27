from datetime import date, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.advanced import MonthlyPassCreate, ReservedSlotCreate
from app.main import create_application


def test_monthly_pass_schema_normalizes_vehicle_and_rejects_reversed_dates() -> None:
    payload = MonthlyPassCreate(
        vehicle_number="ka 01 ab-1234",
        vehicle_type="car",
        holder_name="Fleet Operator",
        valid_from=date(2026, 7, 1),
        valid_until=date(2026, 7, 31),
        amount="1000.00",
    )
    assert payload.vehicle_number == "KA01AB1234"
    with pytest.raises(ValidationError):
        MonthlyPassCreate(
            vehicle_number="KA01AB1234", vehicle_type="car", holder_name="Fleet Operator",
            valid_from=date(2026, 8, 1), valid_until=date(2026, 7, 31), amount="1000.00",
        )


def test_reservation_schema_requires_valid_slot_and_forward_time_range() -> None:
    start = datetime.now()
    with pytest.raises(ValidationError):
        ReservedSlotCreate(
            parking_slot_id="not-an-object-id", vehicle_number="KA01AB1234", holder_name="Fleet Operator",
            valid_from=start, valid_until=start + timedelta(hours=1),
        )
    with pytest.raises(ValidationError):
        ReservedSlotCreate(
            parking_slot_id="507f1f77bcf86cd799439011", vehicle_number="KA01AB1234", holder_name="Fleet Operator",
            valid_from=start, valid_until=start,
        )


def test_openapi_exposes_advanced_parking_and_system_maintenance() -> None:
    schema = create_application().openapi()
    assert "/api/v1/advanced/parking-slots" in schema["paths"]
    assert "/api/v1/system/backup" in schema["paths"]
    assert schema["paths"]["/api/v1/system/backup"]["get"]["tags"] == ["System Maintenance"]
