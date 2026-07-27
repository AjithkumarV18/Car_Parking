from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, model_validator

from app.application.settings.service import SoftwareSettingsService
from app.core.authorization import require_super_admin
from app.core.security import Principal
from app.core.tenant import company_context
from app.infrastructure.database.mongodb import get_database
from app.shared.response import ApiResponse, success_response

router = APIRouter(prefix="/settings", tags=["Software Settings"], dependencies=[Depends(company_context)])


class SoftwareSettingsResponse(BaseModel):
    rfid_entry_enabled: bool
    rfid_exit_enabled: bool
    qr_entry_enabled: bool
    qr_exit_enabled: bool
    webcam_capture_enabled: bool
    vehicle_image_capture_enabled: bool
    advance_payment_enabled: bool
    monthly_pass_lookup_enabled: bool
    auto_open_receipt_enabled: bool


class SoftwareSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rfid_entry_enabled: bool | None = None
    rfid_exit_enabled: bool | None = None
    qr_entry_enabled: bool | None = None
    qr_exit_enabled: bool | None = None
    webcam_capture_enabled: bool | None = None
    vehicle_image_capture_enabled: bool | None = None
    advance_payment_enabled: bool | None = None
    monthly_pass_lookup_enabled: bool | None = None
    auto_open_receipt_enabled: bool | None = None

    @model_validator(mode="after")
    def contains_a_change(self) -> SoftwareSettingsUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one software setting must be provided.")
        return self


def get_settings_service(
    database: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> SoftwareSettingsService:
    return SoftwareSettingsService(database)


@router.get("/software", response_model=ApiResponse[SoftwareSettingsResponse])
async def get_software_settings(
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[SoftwareSettingsService, Depends(get_settings_service)],
    _: Annotated[Principal, Depends(require_super_admin())],
) -> ApiResponse[SoftwareSettingsResponse]:
    return success_response(SoftwareSettingsResponse.model_validate(await service.get(company_id)))


@router.patch("/software", response_model=ApiResponse[SoftwareSettingsResponse])
async def update_software_settings(
    payload: SoftwareSettingsUpdate,
    company_id: Annotated[str, Depends(company_context)],
    principal: Annotated[Principal, Depends(require_super_admin())],
    service: Annotated[SoftwareSettingsService, Depends(get_settings_service)],
) -> ApiResponse[SoftwareSettingsResponse]:
    values = payload.model_dump(exclude_unset=True)
    return success_response(
        SoftwareSettingsResponse.model_validate(await service.update(company_id, values, principal.user_id)),
        message="Software settings updated successfully.",
    )
