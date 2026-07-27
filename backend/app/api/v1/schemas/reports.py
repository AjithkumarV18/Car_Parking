from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from bson import ObjectId
from pydantic import BaseModel, Field, field_validator, model_validator

from app.api.v1.schemas.parking import PaymentMethod, VehicleType

ReportName = Literal[
    "daily-collection",
    "monthly-collection",
    "vehicle",
    "employee-collection",
    "gst",
    "audit",
    "payment",
    "cancelled-receipts",
]
ExportFormat = Literal["excel", "pdf"]


class ReportFilters(BaseModel):
    """Validated shared criteria for tenant reporting endpoints."""

    date_from: date | None = None
    date_to: date | None = None
    search: str | None = Field(default=None, max_length=100)
    location_id: str | None = None
    vehicle_type: VehicleType | None = None
    payment_method: PaymentMethod | None = None

    @field_validator("search")
    @classmethod
    def normalize_search(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None

    @field_validator("location_id")
    @classmethod
    def validate_location_id(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip()
        if not ObjectId.is_valid(normalized):
            raise ValueError("Location ID must be a valid 24-character identifier.")
        return normalized

    @model_validator(mode="after")
    def validate_date_range(self) -> ReportFilters:
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise ValueError("Date from must be on or before date to.")
            if (self.date_to - self.date_from).days > 366:
                raise ValueError("Report date range cannot exceed 366 days.")
        return self


class ReportRevenuePointResponse(BaseModel):
    period: str
    label: str
    amount: str


class PaymentMethodPointResponse(BaseModel):
    method: PaymentMethod
    amount: str
    count: int = Field(ge=0)


class ReportSummaryResponse(BaseModel):
    currency: str = Field(min_length=3, max_length=3)
    date_from: date
    date_to: date
    total_collection: str
    advance_collection: str
    settlement_collection: str
    completed_exits: int = Field(ge=0)
    gst_collected: str
    revenue: list[ReportRevenuePointResponse]
    payment_methods: list[PaymentMethodPointResponse]


class DailyCollectionReportRow(BaseModel):
    period: date
    settlement_collection: str
    advance_collection: str
    total_collection: str
    exit_revenue: str
    gst_amount: str
    exit_count: int = Field(ge=0)


class MonthlyCollectionReportRow(BaseModel):
    period: str
    settlement_collection: str
    advance_collection: str
    total_collection: str
    exit_revenue: str
    gst_amount: str
    exit_count: int = Field(ge=0)


class VehicleReportRow(BaseModel):
    id: str
    vehicle_number: str
    vehicle_type: VehicleType
    token_number: str
    parking_number: str | None
    entry_at: datetime | None
    exit_at: datetime
    duration_minutes: int = Field(ge=0)
    parking_charge: str
    gst_amount: str
    total_amount: str
    advance_applied: str
    paid_amount: str
    payment_method: PaymentMethod | None
    location_name: str | None
    status: Literal["completed"]


class EmployeeCollectionReportRow(BaseModel):
    employee_id: str | None
    employee_name: str
    designation: str | None
    exits_completed: int = Field(ge=0)
    settlement_collection: str
    advance_applied: str
    total_revenue: str
    gst_amount: str


class GstReportRow(BaseModel):
    period: date
    parking_charge: str
    gst_amount: str
    total_amount: str
    exits_completed: int = Field(ge=0)


class AuditReportRow(BaseModel):
    id: str
    occurred_at: datetime
    actor_name: str | None
    action: str
    entity_type: str
    entity_id: str | None
    outcome: str
    details: str | None


class PaymentReportRow(BaseModel):
    id: str
    paid_at: datetime
    vehicle_number: str | None
    token_number: str | None
    amount: str
    method: PaymentMethod
    payment_reference: str | None
    status: Literal["paid"]
    location_name: str | None


class CancelledReceiptReportRow(BaseModel):
    id: str
    receipt_type: Literal["entry", "exit"]
    receipt_number: str | None
    vehicle_number: str | None
    token_number: str | None
    cancelled_at: datetime
    cancelled_by_name: str | None
    reason: str | None
    amount: str | None
    status: Literal["cancelled"]
