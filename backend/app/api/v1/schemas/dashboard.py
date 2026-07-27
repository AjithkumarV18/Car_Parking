from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RevenuePointResponse(BaseModel):
    date: str
    label: str
    amount: str


class VehicleTypePointResponse(BaseModel):
    vehicle_type: str
    count: int = Field(ge=0)


class OccupancyStatusResponse(BaseModel):
    location_id: str | None
    location_name: str
    capacity: int = Field(ge=0)
    occupied: int = Field(ge=0)
    available: int = Field(ge=0)


class RecentActivityResponse(BaseModel):
    id: str
    kind: Literal["entry", "exit"]
    vehicle_number: str
    token_number: str
    occurred_at: datetime
    location_name: str | None
    amount: str | None = None


class DashboardOverviewResponse(BaseModel):
    currency: str = Field(min_length=3, max_length=3)
    today_collection: str
    today_entries: int = Field(ge=0)
    today_exits: int = Field(ge=0)
    monthly_revenue: str
    weekly_revenue: str
    occupied_slots: int = Field(ge=0)
    available_slots: int = Field(ge=0)
    revenue: list[RevenuePointResponse]
    vehicle_types: list[VehicleTypePointResponse]
    occupancy: list[OccupancyStatusResponse]
    recent_activities: list[RecentActivityResponse]
