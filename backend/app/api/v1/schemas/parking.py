from __future__ import annotations

import base64
import binascii
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

VehicleType = Literal["cycle", "bike", "car", "auto", "mini_bus", "bus", "truck"]
PaymentMethod = Literal["cash", "upi", "card"]

VEHICLE_NUMBER_PATTERN = re.compile(r"^[A-Z0-9]{4,20}$")
IMAGE_DATA_PATTERN = re.compile(r"^data:image/(jpeg|png|webp);base64,", re.IGNORECASE)
MAX_IMAGE_BYTES = 2 * 1024 * 1024


class VehicleEntryCreate(BaseModel):
    vehicle_number: str = Field(min_length=4, max_length=32)
    rfid: str | None = Field(default=None, max_length=128)
    qr_code: str | None = Field(default=None, max_length=256)
    vehicle_type: VehicleType
    owner_name: str | None = Field(default=None, min_length=2, max_length=120)
    mobile: str | None = Field(default=None, pattern=r"^\+[1-9][0-9]{7,14}$")
    vehicle_image_data: str | None = Field(default=None, max_length=3_000_000)
    advance_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)

    @field_validator("vehicle_number")
    @classmethod
    def normalize_vehicle_number(cls, value: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9]", "", value).upper()
        if not VEHICLE_NUMBER_PATTERN.fullmatch(normalized):
            raise ValueError("Vehicle number must contain 4 to 20 letters or digits.")
        return normalized

    @field_validator("rfid", "qr_code", "owner_name", "mobile")
    @classmethod
    def trim_optional_values(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None

    @field_validator("vehicle_image_data")
    @classmethod
    def validate_image_data(cls, value: str | None) -> str | None:
        if not value:
            return None
        match = IMAGE_DATA_PATTERN.match(value)
        if not match:
            raise ValueError("Vehicle image must be a JPEG, PNG, or WebP data URL.")
        try:
            raw = base64.b64decode(value[match.end() :], validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("Vehicle image data is invalid.") from exc
        if not raw or len(raw) > MAX_IMAGE_BYTES:
            raise ValueError("Vehicle image must be between 1 byte and 2 MB.")
        return value


class EntryOperatorResponse(BaseModel):
    name: str
    employee_id: str | None = None
    designation: str | None = None


class VehicleEntryResponse(BaseModel):
    id: str
    vehicle_number: str
    rfid: str | None
    qr_code: str | None
    vehicle_type: VehicleType
    entry_at: datetime
    parking_number: str
    token_number: str
    owner_name: str | None
    mobile: str | None
    vehicle_image_available: bool
    advance_amount: str
    location_name: str | None
    operator: EntryOperatorResponse
    status: Literal["open", "closed"]


class OpenEntryOption(BaseModel):
    """Minimal active-session data used to recover a failed exit lookup."""

    id: str
    vehicle_number: str
    token_number: str
    parking_number: str
    vehicle_type: VehicleType
    entry_at: datetime


class VehicleMembershipResponse(BaseModel):
    """Current monthly-pass information shown to an entry or exit operator."""

    vehicle_number: str
    has_active_pass: bool
    pass_number: str | None = None
    holder_name: str | None = None
    valid_until: datetime | None = None
    remaining_days: int = 0
    amount: str | None = None


class EntryLookupQuery(BaseModel):
    vehicle_number: str | None = Field(default=None, max_length=32)
    card: str | None = Field(default=None, max_length=64)
    qr_code: str | None = Field(default=None, max_length=256)
    rfid: str | None = Field(default=None, max_length=128)

    @field_validator("vehicle_number", "card", "qr_code", "rfid")
    @classmethod
    def trim_identifiers(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None

    @model_validator(mode="after")
    def at_least_one_identifier(self) -> EntryLookupQuery:
        if not any((self.vehicle_number, self.card, self.qr_code, self.rfid)):
            raise ValueError("Provide a vehicle number, card/token, QR code, or RFID value.")
        return self


class ExitCalculationResponse(BaseModel):
    entry: VehicleEntryResponse
    duration_minutes: int
    parking_charge: str
    gst_percent: str
    gst_amount: str
    total_amount: str
    advance_amount: str
    advance_applied: str
    paid_amount: str
    balance_amount: str
    rate_effective_date: date


class VehicleExitCreate(BaseModel):
    entry_id: str
    paid_amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    payment_method: PaymentMethod | None = None
    payment_reference: str | None = Field(default=None, max_length=100)

    @field_validator("payment_reference")
    @classmethod
    def trim_payment_reference(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None

    @model_validator(mode="after")
    def require_payment_method_for_money(self) -> VehicleExitCreate:
        if self.paid_amount > 0 and self.payment_method is None:
            raise ValueError("Payment method is required when a paid amount is supplied.")
        return self


class VehicleExitResponse(ExitCalculationResponse):
    id: str
    exit_at: datetime
    payment_method: PaymentMethod | None
    payment_reference: str | None
    status: Literal["completed"]


class ReceiptCompanyResponse(BaseModel):
    company_name: str
    logo_url: str | None = None
    gstin: str | None
    address: str | None
    currency: str
    receipt_footer: str | None


class ReceiptOperatorResponse(BaseModel):
    name: str
    employee_id: str | None = None
    designation: str | None = None


class ParkingReceiptResponse(BaseModel):
    receipt_type: Literal["entry", "exit"]
    receipt_number: str
    qr_payload: str
    barcode_value: str
    issued_at: datetime
    company: ReceiptCompanyResponse
    operator: ReceiptOperatorResponse
    entry: VehicleEntryResponse
    exit: VehicleExitResponse | None = None
