from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, model_validator

from app.application.rates.service import ParkingRateService
from app.core.authorization import require_permissions
from app.core.security import Principal
from app.core.tenant import company_context
from app.infrastructure.database.mongodb import get_database
from app.shared.pagination import Page, PaginationParams
from app.shared.response import ApiResponse, success_response

VehicleType = Literal["cycle", "bike", "car", "auto", "mini_bus", "bus", "truck"]
ParkingRateStatus = Literal["draft", "active", "inactive"]

router = APIRouter(prefix="/parking-rates", tags=["Parking Rate Master"], dependencies=[Depends(company_context)])


class DurationSlabPayload(BaseModel):
    from_minutes: int = Field(ge=0, le=525_600)
    to_minutes: int | None = Field(default=None, ge=0, le=525_600)
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    gst_percent: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)


class ParkingRateBase(BaseModel):
    vehicle_type: VehicleType
    duration_slabs: list[DurationSlabPayload] = Field(min_length=1, max_length=50)
    effective_date: date
    status: ParkingRateStatus = "active"

    @model_validator(mode="after")
    def contiguous_duration_slabs(self) -> ParkingRateBase:
        ParkingRateService.validate_duration_slabs([slab.model_dump(mode="python") for slab in self.duration_slabs])
        return self


class ParkingRateCreate(ParkingRateBase):
    pass


class ParkingRateUpdate(BaseModel):
    vehicle_type: VehicleType | None = None
    duration_slabs: list[DurationSlabPayload] | None = Field(default=None, min_length=1, max_length=50)
    effective_date: date | None = None
    status: ParkingRateStatus | None = None

    @model_validator(mode="after")
    def validate_update(self) -> ParkingRateUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        if self.duration_slabs is not None:
            ParkingRateService.validate_duration_slabs([slab.model_dump(mode="python") for slab in self.duration_slabs])
        return self


class DurationSlabResponse(DurationSlabPayload):
    amount: str
    gst_percent: str


class ParkingRateResponse(BaseModel):
    id: str
    vehicle_type: VehicleType
    duration_slabs: list[DurationSlabResponse]
    effective_date: date
    status: ParkingRateStatus


def get_rate_service(database: Annotated[AsyncIOMotorDatabase, Depends(get_database)]) -> ParkingRateService:
    return ParkingRateService(database)


def filters(
    search: str | None = Query(default=None, max_length=40),
    rate_status: ParkingRateStatus | None = Query(default=None, alias="status"),
    vehicle_type: VehicleType | None = None,
    effective_from: date | None = None,
    effective_to: date | None = None,
    sort_by: Literal["vehicle_type", "effective_date", "status", "created_at"] = "effective_date",
    sort_order: Literal["asc", "desc"] = "desc",
) -> dict[str, Any]:
    return {
        "search": search,
        "status": rate_status,
        "vehicle_type": vehicle_type,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }


@router.get("", response_model=ApiResponse[Page[ParkingRateResponse]])
async def list_parking_rates(
    company_id: Annotated[str, Depends(company_context)],
    pagination: Annotated[PaginationParams, Depends()],
    active_filters: Annotated[dict[str, Any], Depends(filters)],
    service: Annotated[ParkingRateService, Depends(get_rate_service)],
    _: Annotated[Principal, Depends(require_permissions("rate:show"))],
) -> ApiResponse[Page[ParkingRateResponse]]:
    page = await service.list(company_id, pagination, active_filters)
    return success_response(Page[ParkingRateResponse].model_validate(page))


@router.post("", response_model=ApiResponse[ParkingRateResponse], status_code=status.HTTP_201_CREATED)
async def create_parking_rate(
    payload: ParkingRateCreate,
    company_id: Annotated[str, Depends(company_context)],
    principal: Annotated[Principal, Depends(require_permissions("rate:save"))],
    service: Annotated[ParkingRateService, Depends(get_rate_service)],
) -> ApiResponse[ParkingRateResponse]:
    rate = await service.create(company_id, payload.model_dump(mode="python"), principal.user_id)
    return success_response(ParkingRateResponse.model_validate(rate), message="Parking rate created successfully.")


@router.get("/{rate_id}", response_model=ApiResponse[ParkingRateResponse])
async def get_parking_rate(
    rate_id: str,
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[ParkingRateService, Depends(get_rate_service)],
    _: Annotated[Principal, Depends(require_permissions("rate:details"))],
) -> ApiResponse[ParkingRateResponse]:
    return success_response(ParkingRateResponse.model_validate(await service.get(company_id, rate_id)))


@router.patch("/{rate_id}", response_model=ApiResponse[ParkingRateResponse])
async def update_parking_rate(
    rate_id: str,
    payload: ParkingRateUpdate,
    company_id: Annotated[str, Depends(company_context)],
    principal: Annotated[Principal, Depends(require_permissions("rate:edit"))],
    service: Annotated[ParkingRateService, Depends(get_rate_service)],
) -> ApiResponse[ParkingRateResponse]:
    rate = await service.update(company_id, rate_id, payload.model_dump(exclude_unset=True, mode="python"), principal.user_id)
    return success_response(ParkingRateResponse.model_validate(rate), message="Parking rate updated successfully.")


@router.delete("/{rate_id}", response_model=ApiResponse[None])
async def delete_parking_rate(
    rate_id: str,
    company_id: Annotated[str, Depends(company_context)],
    principal: Annotated[Principal, Depends(require_permissions("rate:delete"))],
    service: Annotated[ParkingRateService, Depends(get_rate_service)],
) -> ApiResponse[None]:
    await service.deactivate(company_id, rate_id, principal.user_id)
    return success_response(message="Parking rate deactivated successfully.")
