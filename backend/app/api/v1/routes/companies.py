from __future__ import annotations

import re
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator, model_validator

from app.application.companies.service import CompanyService
from app.core.authorization import require_super_admin
from app.core.security import Principal
from app.core.tenant import company_context
from app.infrastructure.database.mongodb import get_database
from app.shared.image_data import validate_image_reference
from app.shared.pagination import Page, PaginationParams
from app.shared.phone import normalize_indian_phone
from app.shared.response import ApiResponse, success_response

router = APIRouter(
    prefix="/companies",
    tags=["Company Management"],
    dependencies=[Depends(company_context), Depends(require_super_admin())],
)

GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


class AddressPayload(BaseModel):
    line1: str = Field(min_length=2, max_length=160)
    line2: str | None = Field(default=None, max_length=160)
    city: str = Field(min_length=2, max_length=80)
    state: str = Field(min_length=2, max_length=80)
    postal_code: str = Field(min_length=3, max_length=16)
    country_code: str = Field(default="IN", min_length=2, max_length=2)

    @field_validator("country_code")
    @classmethod
    def uppercase_country(cls, value: str) -> str:
        return value.upper()


class ThemePayload(BaseModel):
    primary_color: str = "#0B4F6C"
    secondary_color: str = "#EF8354"
    logo_url: HttpUrl | None = None

    @field_validator("primary_color", "secondary_color")
    @classmethod
    def valid_hex_color(cls, value: str) -> str:
        if not HEX_COLOR_PATTERN.fullmatch(value):
            raise ValueError("Theme colors must be in #RRGGBB format.")
        return value.upper()


class CompanyBase(BaseModel):
    company_name: str = Field(min_length=2, max_length=160)
    code: str | None = Field(default=None, min_length=2, max_length=40)
    logo_url: str | None = Field(default=None, max_length=3_000_000)
    address: AddressPayload
    gstin: str | None = Field(default=None, max_length=15)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    theme: ThemePayload = Field(default_factory=ThemePayload)
    receipt_footer: str | None = Field(default=None, max_length=1000)
    phone: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")
    email: EmailStr
    date_format: Literal["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"] = "DD/MM/YYYY"
    time_format: Literal["12h", "24h"] = "24h"
    timezone: str = Field(default="Asia/Kolkata", min_length=3, max_length=64)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return value.upper().strip() if value else None

    @field_validator("logo_url", mode="before")
    @classmethod
    def normalize_blank_logo(cls, value: str | None) -> str | None:
        return validate_image_reference(value, label="Company logo")

    @field_validator("email", mode="before")
    @classmethod
    def trim_email(cls, value: str) -> str:
        return value.strip()

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: str) -> str | None:
        return normalize_indian_phone(value)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.upper().strip()
        if not GSTIN_PATTERN.fullmatch(normalized):
            raise ValueError("GSTIN must be a valid 15-character Indian GST number.")
        return normalized


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    company_name: str | None = Field(default=None, min_length=2, max_length=160)
    code: str | None = Field(default=None, min_length=2, max_length=40)
    logo_url: str | None = Field(default=None, max_length=3_000_000)
    address: AddressPayload | None = None
    gstin: str | None = Field(default=None, max_length=15)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    theme: ThemePayload | None = None
    receipt_footer: str | None = Field(default=None, max_length=1000)
    phone: str | None = Field(default=None, pattern=r"^\+[1-9][0-9]{7,14}$")
    email: EmailStr | None = None
    date_format: Literal["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"] | None = None
    time_format: Literal["12h", "24h"] | None = None
    timezone: str | None = Field(default=None, min_length=3, max_length=64)

    @field_validator("code")
    @classmethod
    def normalize_update_code(cls, value: str | None) -> str | None:
        return value.upper().strip() if value else value

    @field_validator("logo_url", mode="before")
    @classmethod
    def normalize_update_logo(cls, value: str | None) -> str | None:
        return validate_image_reference(value, label="Company logo")

    @field_validator("currency")
    @classmethod
    def normalize_update_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @field_validator("gstin")
    @classmethod
    def validate_update_gstin(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return value
        normalized = value.upper().strip()
        if not GSTIN_PATTERN.fullmatch(normalized):
            raise ValueError("GSTIN must be a valid 15-character Indian GST number.")
        return normalized

    @model_validator(mode="after")
    def not_empty(self) -> CompanyUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        return self


class CompanyResponse(CompanyBase):
    id: str
    status: str


class BranchBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str | None = Field(default=None, min_length=2, max_length=40)
    address: AddressPayload
    phone: str | None = Field(default=None, pattern=r"^\+[1-9][0-9]{7,14}$")
    email: EmailStr | None = None
    timezone: str = Field(default="Asia/Kolkata", min_length=3, max_length=64)

    @field_validator("code")
    @classmethod
    def normalize_branch_code(cls, value: str | None) -> str | None:
        return value.upper().strip() if value else None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_blank_email(cls, value: str | None) -> str | None:
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        return normalize_indian_phone(value)


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    code: str | None = Field(default=None, min_length=2, max_length=40)
    address: AddressPayload | None = None
    phone: str | None = Field(default=None, pattern=r"^\+[1-9][0-9]{7,14}$")
    email: EmailStr | None = None
    timezone: str | None = Field(default=None, min_length=3, max_length=64)


class BranchResponse(BranchBase):
    id: str
    company_id: str
    status: str


class GeoPoint(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float]

    @field_validator("coordinates")
    @classmethod
    def valid_coordinates(cls, value: tuple[float, float]) -> tuple[float, float]:
        longitude, latitude = value
        if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
            raise ValueError("Coordinates must be valid longitude, latitude values.")
        return value


class ParkingLocationBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str | None = Field(default=None, min_length=2, max_length=40)
    address: AddressPayload
    geo: GeoPoint | None = None
    capacity: int = Field(default=0, ge=0, le=100_000)
    phone: str | None = Field(default=None, pattern=r"^\+[1-9][0-9]{7,14}$")

    @field_validator("code")
    @classmethod
    def normalize_location_code(cls, value: str | None) -> str | None:
        return value.upper().strip() if value else None

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_blank_phone(cls, value: str | None) -> str | None:
        return normalize_indian_phone(value)


class ParkingLocationCreate(ParkingLocationBase):
    pass


class ParkingLocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    code: str | None = Field(default=None, min_length=2, max_length=40)
    address: AddressPayload | None = None
    geo: GeoPoint | None = None
    capacity: int | None = Field(default=None, ge=0, le=100_000)
    phone: str | None = Field(default=None, pattern=r"^\+[1-9][0-9]{7,14}$")


class ParkingLocationResponse(ParkingLocationBase):
    id: str
    company_id: str
    branch_id: str
    status: str


def get_company_service(
    database: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> CompanyService:
    return CompanyService(database)


@router.get("", response_model=ApiResponse[Page[CompanyResponse]])
async def list_companies(
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[CompanyService, Depends(get_company_service)],
) -> ApiResponse[Page[CompanyResponse]]:
    page = await service.list_companies(pagination)
    return success_response(Page[CompanyResponse].model_validate(page))


@router.get("/{company_id}", response_model=ApiResponse[CompanyResponse])
async def get_company(
    company_id: str,
    service: Annotated[CompanyService, Depends(get_company_service)],
) -> ApiResponse[CompanyResponse]:
    return success_response(CompanyResponse.model_validate(await service.get_company(company_id)))


@router.patch("/{company_id}", response_model=ApiResponse[CompanyResponse])
async def update_company(
    company_id: str,
    payload: CompanyUpdate,
    principal: Annotated[Principal, Depends(require_super_admin())],
    service: Annotated[CompanyService, Depends(get_company_service)],
) -> ApiResponse[CompanyResponse]:
    company = await service.update_company(
        company_id,
        payload.model_dump(exclude_unset=True, mode="json"),
        principal.user_id,
    )
    return success_response(CompanyResponse.model_validate(company), message="Company updated successfully.")


@router.get("/{company_id}/branches", response_model=ApiResponse[Page[BranchResponse]])
async def list_branches(
    company_id: str,
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[CompanyService, Depends(get_company_service)],
) -> ApiResponse[Page[BranchResponse]]:
    page = await service.list_branches(company_id, pagination)
    return success_response(Page[BranchResponse].model_validate(page))


@router.post("/{company_id}/branches", response_model=ApiResponse[BranchResponse], status_code=status.HTTP_201_CREATED)
async def create_branch(
    company_id: str,
    payload: BranchCreate,
    principal: Annotated[Principal, Depends(require_super_admin())],
    service: Annotated[CompanyService, Depends(get_company_service)],
) -> ApiResponse[BranchResponse]:
    branch = await service.create_branch(company_id, payload.model_dump(mode="json"), principal.user_id)
    return success_response(BranchResponse.model_validate(branch), message="Branch created successfully.")


@router.patch("/{company_id}/branches/{branch_id}", response_model=ApiResponse[BranchResponse])
async def update_branch(
    company_id: str,
    branch_id: str,
    payload: BranchUpdate,
    principal: Annotated[Principal, Depends(require_super_admin())],
    service: Annotated[CompanyService, Depends(get_company_service)],
) -> ApiResponse[BranchResponse]:
    branch = await service.update_branch(
        company_id,
        branch_id,
        payload.model_dump(exclude_unset=True, mode="json"),
        principal.user_id,
    )
    return success_response(BranchResponse.model_validate(branch), message="Branch updated successfully.")


@router.delete("/{company_id}/branches/{branch_id}", response_model=ApiResponse[None])
async def delete_branch(
    company_id: str,
    branch_id: str,
    principal: Annotated[Principal, Depends(require_super_admin())],
    service: Annotated[CompanyService, Depends(get_company_service)],
) -> ApiResponse[None]:
    await service.deactivate_branch(company_id, branch_id, principal.user_id)
    return success_response(message="Branch deactivated successfully.")


@router.get("/{company_id}/branches/{branch_id}/locations", response_model=ApiResponse[Page[ParkingLocationResponse]])
async def list_locations(
    company_id: str,
    branch_id: str,
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[CompanyService, Depends(get_company_service)],
) -> ApiResponse[Page[ParkingLocationResponse]]:
    page = await service.list_locations(company_id, branch_id, pagination)
    return success_response(Page[ParkingLocationResponse].model_validate(page))


@router.post(
    "/{company_id}/branches/{branch_id}/locations",
    response_model=ApiResponse[ParkingLocationResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_location(
    company_id: str,
    branch_id: str,
    payload: ParkingLocationCreate,
    principal: Annotated[Principal, Depends(require_super_admin())],
    service: Annotated[CompanyService, Depends(get_company_service)],
) -> ApiResponse[ParkingLocationResponse]:
    location = await service.create_location(
        company_id,
        branch_id,
        payload.model_dump(mode="json"),
        principal.user_id,
    )
    return success_response(ParkingLocationResponse.model_validate(location), message="Location created successfully.")


@router.patch(
    "/{company_id}/branches/{branch_id}/locations/{location_id}",
    response_model=ApiResponse[ParkingLocationResponse],
)
async def update_location(
    company_id: str,
    branch_id: str,
    location_id: str,
    payload: ParkingLocationUpdate,
    principal: Annotated[Principal, Depends(require_super_admin())],
    service: Annotated[CompanyService, Depends(get_company_service)],
) -> ApiResponse[ParkingLocationResponse]:
    location = await service.update_location(
        company_id,
        branch_id,
        location_id,
        payload.model_dump(exclude_unset=True, mode="json"),
        principal.user_id,
    )
    return success_response(ParkingLocationResponse.model_validate(location), message="Location updated successfully.")


@router.delete("/{company_id}/branches/{branch_id}/locations/{location_id}", response_model=ApiResponse[None])
async def delete_location(
    company_id: str,
    branch_id: str,
    location_id: str,
    principal: Annotated[Principal, Depends(require_super_admin())],
    service: Annotated[CompanyService, Depends(get_company_service)],
) -> ApiResponse[None]:
    await service.deactivate_location(company_id, branch_id, location_id, principal.user_id)
    return success_response(message="Parking location deactivated successfully.")
