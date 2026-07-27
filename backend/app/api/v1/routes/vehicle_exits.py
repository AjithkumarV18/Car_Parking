from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.v1.schemas.parking import (
    EntryLookupQuery,
    ExitCalculationResponse,
    OpenEntryOption,
    ParkingReceiptResponse,
    VehicleEntryResponse,
    VehicleExitCreate,
    VehicleExitResponse,
)
from app.application.parking.service import ParkingOperationsService
from app.core.authorization import require_permissions
from app.core.security import Principal
from app.core.tenant import company_context
from app.infrastructure.database.mongodb import get_database
from app.shared.pagination import Page, PaginationParams
from app.shared.response import ApiResponse, success_response

router = APIRouter(prefix="/vehicle-exits", tags=["Vehicle Exit"], dependencies=[Depends(company_context)])


def get_parking_service(database: Annotated[AsyncIOMotorDatabase, Depends(get_database)]) -> ParkingOperationsService:
    return ParkingOperationsService(database)


@router.get("", response_model=ApiResponse[Page[VehicleExitResponse]])
async def list_vehicle_exit_log(
    pagination: Annotated[PaginationParams, Depends()],
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[ParkingOperationsService, Depends(get_parking_service)],
    _: Annotated[Principal, Depends(require_permissions("parking_exit:show"))],
    search: str | None = None,
) -> ApiResponse[Page[VehicleExitResponse]]:
    return success_response(Page[VehicleExitResponse].model_validate(await service.exit_log(company_id, pagination, search)))


@router.get("/lookup", response_model=ApiResponse[VehicleEntryResponse])
async def lookup_vehicle_entry(
    lookup: Annotated[EntryLookupQuery, Depends()],
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[ParkingOperationsService, Depends(get_parking_service)],
    _: Annotated[Principal, Depends(require_permissions("parking_exit:show"))],
) -> ApiResponse[VehicleEntryResponse]:
    entry = await service.lookup_open_entry(company_id, lookup.model_dump())
    return success_response(VehicleEntryResponse.model_validate(entry))


@router.get("/open-entries", response_model=ApiResponse[list[OpenEntryOption]])
async def list_open_vehicle_entries(
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[ParkingOperationsService, Depends(get_parking_service)],
    _: Annotated[Principal, Depends(require_permissions("parking_exit:show"))],
    search: str | None = None,
) -> ApiResponse[list[OpenEntryOption]]:
    entries = await service.recent_open_entries(company_id, search)
    return success_response([OpenEntryOption.model_validate(entry) for entry in entries])


@router.get("/{entry_id}/calculate", response_model=ApiResponse[ExitCalculationResponse])
async def calculate_vehicle_exit(
    entry_id: str,
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[ParkingOperationsService, Depends(get_parking_service)],
    _: Annotated[Principal, Depends(require_permissions("parking_exit:show"))],
) -> ApiResponse[ExitCalculationResponse]:
    return success_response(ExitCalculationResponse.model_validate(await service.calculate_exit(company_id, entry_id)))


@router.post("", response_model=ApiResponse[VehicleExitResponse], status_code=status.HTTP_201_CREATED)
async def create_vehicle_exit(
    payload: VehicleExitCreate,
    company_id: Annotated[str, Depends(company_context)],
    principal: Annotated[Principal, Depends(require_permissions("parking_exit:save"))],
    service: Annotated[ParkingOperationsService, Depends(get_parking_service)],
) -> ApiResponse[VehicleExitResponse]:
    vehicle_exit = await service.create_exit(company_id, payload.model_dump(mode="python"), principal.user_id)
    return success_response(VehicleExitResponse.model_validate(vehicle_exit), message="Vehicle exit completed successfully.")


@router.get(
    "/{exit_id}/receipt",
    response_model=ApiResponse[ParkingReceiptResponse],
    responses={
        404: {"description": "Vehicle exit receipt was not found."},
        422: {"description": "Receipt ID is invalid."},
        503: {"description": "Receipt data is temporarily unavailable."},
    },
)
async def get_exit_receipt(
    exit_id: str,
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[ParkingOperationsService, Depends(get_parking_service)],
    _: Annotated[Principal, Depends(require_permissions("parking_exit:details"))],
) -> ApiResponse[ParkingReceiptResponse]:
    return success_response(ParkingReceiptResponse.model_validate(await service.exit_receipt(company_id, exit_id)))
