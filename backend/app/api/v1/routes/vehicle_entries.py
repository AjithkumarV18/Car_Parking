from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.v1.schemas.parking import ParkingReceiptResponse, VehicleEntryCreate, VehicleEntryResponse, VehicleMembershipResponse
from app.application.parking.service import ParkingOperationsService
from app.core.authorization import require_any_permissions, require_permissions
from app.core.security import Principal
from app.core.tenant import company_context
from app.infrastructure.database.mongodb import get_database
from app.shared.pagination import Page, PaginationParams
from app.shared.response import ApiResponse, success_response

router = APIRouter(prefix="/vehicle-entries", tags=["Vehicle Entry"], dependencies=[Depends(company_context)])


def get_parking_service(database: Annotated[AsyncIOMotorDatabase, Depends(get_database)]) -> ParkingOperationsService:
    return ParkingOperationsService(database)


@router.post("", response_model=ApiResponse[VehicleEntryResponse], status_code=status.HTTP_201_CREATED)
async def create_vehicle_entry(
    payload: VehicleEntryCreate,
    company_id: Annotated[str, Depends(company_context)],
    principal: Annotated[Principal, Depends(require_permissions("parking_entry:save"))],
    service: Annotated[ParkingOperationsService, Depends(get_parking_service)],
) -> ApiResponse[VehicleEntryResponse]:
    entry = await service.create_entry(company_id, payload.model_dump(mode="python"), principal.user_id)
    return success_response(VehicleEntryResponse.model_validate(entry), message="Vehicle entry created successfully.")


@router.get("", response_model=ApiResponse[Page[VehicleEntryResponse]])
async def list_vehicle_entry_log(
    pagination: Annotated[PaginationParams, Depends()],
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[ParkingOperationsService, Depends(get_parking_service)],
    _: Annotated[Principal, Depends(require_permissions("parking_entry:show"))],
    search: str | None = Query(default=None, max_length=32),
) -> ApiResponse[Page[VehicleEntryResponse]]:
    return success_response(Page[VehicleEntryResponse].model_validate(await service.entry_log(company_id, pagination, search)))


@router.get("/membership", response_model=ApiResponse[VehicleMembershipResponse])
async def lookup_vehicle_membership(
    vehicle_number: str = Query(min_length=4, max_length=32),
    company_id: str = Depends(company_context),
    service: ParkingOperationsService = Depends(get_parking_service),
    _: Principal = Depends(require_any_permissions("parking_entry:show", "parking_exit:show")),
) -> ApiResponse[VehicleMembershipResponse]:
    return success_response(VehicleMembershipResponse.model_validate(await service.active_membership(company_id, vehicle_number)))


@router.get("/{entry_id}", response_model=ApiResponse[VehicleEntryResponse])
async def get_vehicle_entry(
    entry_id: str,
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[ParkingOperationsService, Depends(get_parking_service)],
    _: Annotated[Principal, Depends(require_permissions("parking_entry:details"))],
) -> ApiResponse[VehicleEntryResponse]:
    return success_response(VehicleEntryResponse.model_validate(await service.get_entry(company_id, entry_id)))


@router.get(
    "/{entry_id}/receipt",
    response_model=ApiResponse[ParkingReceiptResponse],
    responses={
        404: {"description": "Vehicle entry receipt was not found."},
        422: {"description": "Receipt ID is invalid."},
        503: {"description": "Receipt data is temporarily unavailable."},
    },
)
async def get_entry_receipt(
    entry_id: str,
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[ParkingOperationsService, Depends(get_parking_service)],
    _: Annotated[Principal, Depends(require_permissions("parking_entry:details"))],
) -> ApiResponse[ParkingReceiptResponse]:
    return success_response(ParkingReceiptResponse.model_validate(await service.entry_receipt(company_id, entry_id)))


@router.get("/{entry_id}/image")
async def get_entry_image(
    entry_id: str,
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[ParkingOperationsService, Depends(get_parking_service)],
    _: Annotated[Principal, Depends(require_permissions("parking_entry:details"))],
) -> Response:
    content, media_type = await service.entry_image(company_id, entry_id)
    return Response(content=content, media_type=media_type)
