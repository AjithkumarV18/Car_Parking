from __future__ import annotations

from datetime import UTC, datetime

import pytest
from bson import ObjectId
from bson.decimal128 import Decimal128
from pymongo.errors import ServerSelectionTimeoutError

from app.api.v1.schemas.parking import ParkingReceiptResponse
from app.application.parking.service import ParkingOperationsService
from app.core.exceptions import DatabaseUnavailableError, InvalidReceiptIdError, NotFoundError

VALID_ID = "507f1f77bcf86cd799439011"


class _Collection:
    def __init__(self, result: dict | None = None) -> None:
        self.result = result

    async def find_one(self, _query: dict) -> dict | None:
        return self.result


class _Database:
    def __init__(self, *, company: dict | None, entry: dict | None = None, vehicle_exit: dict | None = None) -> None:
        self.companies = _Collection(company)
        self.vehicle_entries = _Collection(entry)
        self.vehicle_exits = _Collection(vehicle_exit)


class _UnavailableCollection:
    async def find_one(self, _query: dict) -> dict | None:
        raise ServerSelectionTimeoutError("MongoDB is unavailable")


class _UnavailableDatabase:
    companies = _UnavailableCollection()


@pytest.mark.asyncio
async def test_receipt_retrieval_rejects_invalid_ids_without_a_database() -> None:
    service = ParkingOperationsService(None)

    with pytest.raises(InvalidReceiptIdError) as entry_error:
        await service.entry_receipt(VALID_ID, "not-an-object-id")
    with pytest.raises(InvalidReceiptIdError) as exit_error:
        await service.exit_receipt(VALID_ID, "also-invalid")

    assert entry_error.value.status_code == 422
    assert entry_error.value.code == "invalid_receipt_id"
    assert exit_error.value.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "message"),
    [("entry_receipt", "Vehicle entry receipt was not found"), ("exit_receipt", "Vehicle exit receipt was not found")],
)
async def test_receipt_returns_a_clear_not_found_error(method: str, message: str) -> None:
    service = ParkingOperationsService(_Database(company={"_id": ObjectId(VALID_ID), "status": "active"}))

    with pytest.raises(NotFoundError, match=message) as error:
        await getattr(service, method)(VALID_ID, VALID_ID)

    assert error.value.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["entry_receipt", "exit_receipt"])
async def test_receipt_database_failure_is_retryable_service_unavailable(method: str) -> None:
    service = ParkingOperationsService(_UnavailableDatabase())

    with pytest.raises(DatabaseUnavailableError, match="temporarily unavailable") as error:
        await getattr(service, method)(VALID_ID, VALID_ID)

    assert error.value.status_code == 503
    assert error.value.code == "database_unavailable"


@pytest.mark.asyncio
async def test_entry_receipt_contains_thermal_print_identifiers_and_operator() -> None:
    company_id = ObjectId(VALID_ID)
    database = _Database(
        company={
            "_id": company_id,
            "status": "active",
            "company_name": "North Yard Parking",
            "logo_url": "https://example.com/logo.png",
            "currency": "INR",
        },
        entry={
            "_id": ObjectId(VALID_ID),
            "company_id": company_id,
            "vehicle_number": "KA01AB1234",
            "rfid": None,
            "qr_code": None,
            "vehicle_type": "car",
            "entry_at": datetime.now(UTC),
            "parking_number": "P-20260726-00001",
            "token_number": "T-20260726-00001",
            "owner_name": None,
            "mobile": None,
            "advance_amount": Decimal128("20.00"),
            "entry_by": company_id,
            "status": "open",
        },
    )
    database.employees = _Collection(None)
    database.users = _Collection(None)

    receipt = ParkingReceiptResponse.model_validate(await ParkingOperationsService(database).entry_receipt(VALID_ID, VALID_ID))

    assert receipt.receipt_number == "EN-T-20260726-00001"
    assert receipt.qr_payload == receipt.receipt_number
    assert receipt.barcode_value == receipt.receipt_number
    assert receipt.company.logo_url == "https://example.com/logo.png"
    assert receipt.operator.name == "System"
