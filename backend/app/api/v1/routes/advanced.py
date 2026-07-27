from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.v1.schemas.advanced import (
    MonthlyPassCreate,
    MonthlyPassResponse,
    MonthlyPassUpdate,
    ParkingLocationOption,
    ParkingSlotCreate,
    ParkingSlotResponse,
    ParkingSlotUpdate,
    ReservedSlotCreate,
    ReservedSlotResponse,
    ReservedSlotUpdate,
)
from app.application.advanced.service import AdvancedParkingService
from app.core.authorization import require_permissions
from app.core.security import Principal
from app.core.tenant import company_context
from app.infrastructure.database.mongodb import get_database
from app.shared.response import ApiResponse, success_response

router = APIRouter(prefix="/advanced", tags=["Advanced Parking"], dependencies=[Depends(company_context)])


def service(database: Annotated[AsyncIOMotorDatabase, Depends(get_database)]) -> AdvancedParkingService:
    return AdvancedParkingService(database)


@router.get("/parking-locations", response_model=ApiResponse[list[ParkingLocationOption]])
async def locations(
    company_id: Annotated[str, Depends(company_context)],
    svc: Annotated[AdvancedParkingService, Depends(service)],
    _: Annotated[Principal, Depends(require_permissions("advanced:show"))],
) -> ApiResponse[list[ParkingLocationOption]]:
    return success_response([ParkingLocationOption.model_validate(item) for item in await svc.locations(company_id)])


@router.get("/monthly-passes", response_model=ApiResponse[list[MonthlyPassResponse]])
async def list_passes(
    company_id: Annotated[str, Depends(company_context)],
    svc: Annotated[AdvancedParkingService, Depends(service)],
    _: Annotated[Principal, Depends(require_permissions("advanced:show"))],
) -> ApiResponse[list[MonthlyPassResponse]]:
    return success_response([MonthlyPassResponse.model_validate(item) for item in await svc.passes(company_id)])


@router.post("/monthly-passes", response_model=ApiResponse[MonthlyPassResponse], status_code=status.HTTP_201_CREATED)
async def create_pass(
    payload: MonthlyPassCreate,
    company_id: Annotated[str, Depends(company_context)],
    principal: Annotated[Principal, Depends(require_permissions("advanced:manage"))],
    svc: Annotated[AdvancedParkingService, Depends(service)],
) -> ApiResponse[MonthlyPassResponse]:
    item = await svc.create_pass(company_id, payload.model_dump(), principal.user_id)
    return success_response(MonthlyPassResponse.model_validate(item), message="Monthly pass created.")


@router.patch("/monthly-passes/{pass_id}", response_model=ApiResponse[MonthlyPassResponse])
async def update_pass(
    pass_id: str,
    payload: MonthlyPassUpdate,
    company_id: Annotated[str, Depends(company_context)],
    _: Annotated[Principal, Depends(require_permissions("advanced:manage"))],
    svc: Annotated[AdvancedParkingService, Depends(service)],
) -> ApiResponse[MonthlyPassResponse]:
    item = await svc.update_pass(company_id, pass_id, payload.model_dump(exclude_unset=True))
    return success_response(MonthlyPassResponse.model_validate(item), message="Monthly pass updated.")


@router.get("/parking-slots", response_model=ApiResponse[list[ParkingSlotResponse]])
async def list_slots(
    company_id: Annotated[str, Depends(company_context)],
    svc: Annotated[AdvancedParkingService, Depends(service)],
    _: Annotated[Principal, Depends(require_permissions("advanced:show"))],
    location_id: str | None = None,
) -> ApiResponse[list[ParkingSlotResponse]]:
    return success_response([ParkingSlotResponse.model_validate(item) for item in await svc.slots(company_id, location_id)])


@router.post("/parking-slots", response_model=ApiResponse[ParkingSlotResponse], status_code=status.HTTP_201_CREATED)
async def create_slot(
    payload: ParkingSlotCreate,
    company_id: Annotated[str, Depends(company_context)],
    principal: Annotated[Principal, Depends(require_permissions("advanced:manage"))],
    svc: Annotated[AdvancedParkingService, Depends(service)],
) -> ApiResponse[ParkingSlotResponse]:
    item = await svc.create_slot(company_id, payload.model_dump(), principal.user_id)
    return success_response(ParkingSlotResponse.model_validate(item), message="Parking slot created.")


@router.patch("/parking-slots/{slot_id}", response_model=ApiResponse[ParkingSlotResponse])
async def update_slot(
    slot_id: str,
    payload: ParkingSlotUpdate,
    company_id: Annotated[str, Depends(company_context)],
    _: Annotated[Principal, Depends(require_permissions("advanced:manage"))],
    svc: Annotated[AdvancedParkingService, Depends(service)],
) -> ApiResponse[ParkingSlotResponse]:
    item = await svc.update_slot(company_id, slot_id, payload.model_dump(exclude_unset=True))
    return success_response(ParkingSlotResponse.model_validate(item), message="Parking slot updated.")


@router.get("/reserved-slots", response_model=ApiResponse[list[ReservedSlotResponse]])
async def list_reservations(
    company_id: Annotated[str, Depends(company_context)],
    svc: Annotated[AdvancedParkingService, Depends(service)],
    _: Annotated[Principal, Depends(require_permissions("advanced:show"))],
) -> ApiResponse[list[ReservedSlotResponse]]:
    return success_response([ReservedSlotResponse.model_validate(item) for item in await svc.reservations(company_id)])


@router.post("/reserved-slots", response_model=ApiResponse[ReservedSlotResponse], status_code=status.HTTP_201_CREATED)
async def create_reservation(
    payload: ReservedSlotCreate,
    company_id: Annotated[str, Depends(company_context)],
    principal: Annotated[Principal, Depends(require_permissions("advanced:manage"))],
    svc: Annotated[AdvancedParkingService, Depends(service)],
) -> ApiResponse[ReservedSlotResponse]:
    item = await svc.create_reservation(company_id, payload.model_dump(), principal.user_id)
    return success_response(ReservedSlotResponse.model_validate(item), message="Slot reservation created.")


@router.patch("/reserved-slots/{reservation_id}", response_model=ApiResponse[ReservedSlotResponse])
async def update_reservation(
    reservation_id: str,
    payload: ReservedSlotUpdate,
    company_id: Annotated[str, Depends(company_context)],
    _: Annotated[Principal, Depends(require_permissions("advanced:manage"))],
    svc: Annotated[AdvancedParkingService, Depends(service)],
) -> ApiResponse[ReservedSlotResponse]:
    item = await svc.update_reservation(company_id, reservation_id, payload.model_dump(exclude_unset=True))
    return success_response(ReservedSlotResponse.model_validate(item), message="Slot reservation updated.")
