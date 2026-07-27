from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from bson import ObjectId
from pydantic import BaseModel, Field, field_validator, model_validator

from app.api.v1.schemas.parking import VehicleType

SlotStatus = Literal["available", "occupied", "reserved", "maintenance"]
PassStatus = Literal["active", "expired", "suspended"]
ReservationStatus = Literal["active", "cancelled", "completed"]
ReservationDisplayStatus = Literal["active", "cancelled", "completed", "expired"]


def _valid_object_id(value: str) -> str:
    if not ObjectId.is_valid(value):
        raise ValueError("Must be a valid 24-character identifier.")
    return value


class MonthlyPassCreate(BaseModel):
    vehicle_number: str = Field(min_length=4, max_length=20)
    vehicle_type: VehicleType
    holder_name: str = Field(min_length=2, max_length=120)
    mobile: str | None = Field(default=None, pattern=r"^\+[1-9][0-9]{7,14}$")
    parking_location_id: str | None = None
    valid_from: date
    valid_until: date
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    status: PassStatus = "active"

    @field_validator("vehicle_number")
    @classmethod
    def normalize_vehicle(cls, value: str) -> str:
        return "".join(char for char in value.upper() if char.isalnum())

    @field_validator("mobile", mode="before")
    @classmethod
    def normalize_indian_mobile(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return None
        normalized = re.sub(r"[\s()-]", "", str(value))
        if re.fullmatch(r"[6-9][0-9]{9}", normalized):
            return f"+91{normalized}"
        if re.fullmatch(r"0[6-9][0-9]{9}", normalized):
            return f"+91{normalized[1:]}"
        if re.fullmatch(r"91[6-9][0-9]{9}", normalized):
            return f"+{normalized}"
        return normalized

    @field_validator("parking_location_id")
    @classmethod
    def validate_location(cls, value: str | None) -> str | None:
        return _valid_object_id(value) if value else None

    @model_validator(mode="after")
    def validate_validity(self) -> MonthlyPassCreate:
        if self.valid_until < self.valid_from:
            raise ValueError("Pass end date must not be before its start date.")
        return self


class MonthlyPassUpdate(BaseModel):
    holder_name: str | None = Field(default=None, min_length=2, max_length=120)
    mobile: str | None = Field(default=None, pattern=r"^\+[1-9][0-9]{7,14}$")
    valid_until: date | None = None
    amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    status: PassStatus | None = None


class MonthlyPassResponse(MonthlyPassCreate):
    id: str
    pass_number: str
    created_at: datetime


class ParkingLocationOption(BaseModel):
    id: str
    name: str
    branch_name: str | None = None


class ParkingSlotCreate(BaseModel):
    parking_location_id: str
    slot_number: str = Field(min_length=1, max_length=40)
    vehicle_type: VehicleType | None = None
    status: SlotStatus = "available"

    @field_validator("parking_location_id")
    @classmethod
    def validate_location(cls, value: str) -> str:
        return _valid_object_id(value)

    @field_validator("slot_number")
    @classmethod
    def normalize_slot(cls, value: str) -> str:
        return value.upper().strip()


class ParkingSlotUpdate(BaseModel):
    vehicle_type: VehicleType | None = None
    status: SlotStatus | None = None


class ParkingSlotResponse(ParkingSlotCreate):
    id: str
    reserved_for: str | None = None
    occupied_by: str | None = None


class ReservedSlotCreate(BaseModel):
    parking_slot_id: str
    vehicle_number: str = Field(min_length=4, max_length=20)
    holder_name: str = Field(min_length=2, max_length=120)
    valid_from: datetime
    valid_until: datetime
    status: ReservationStatus = "active"

    @field_validator("parking_slot_id")
    @classmethod
    def validate_slot(cls, value: str) -> str:
        return _valid_object_id(value)

    @field_validator("vehicle_number")
    @classmethod
    def normalize_vehicle(cls, value: str) -> str:
        return "".join(char for char in value.upper() if char.isalnum())

    @model_validator(mode="after")
    def validate_validity(self) -> ReservedSlotCreate:
        if self.valid_until <= self.valid_from:
            raise ValueError("Reservation end must be after its start.")
        return self


class ReservedSlotUpdate(BaseModel):
    holder_name: str | None = Field(default=None, min_length=2, max_length=120)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    status: ReservationStatus | None = None


class ReservedSlotResponse(ReservedSlotCreate):
    id: str
    slot_number: str | None = None
    status: ReservationDisplayStatus
    created_at: datetime
