from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.api.v1.routes.companies import AddressPayload, CompanyCreate, CompanyResponse
from app.application.setup.service import SetupService
from app.infrastructure.database.mongodb import get_database
from app.shared.image_data import validate_image_reference
from app.shared.phone import normalize_indian_phone
from app.shared.response import ApiResponse, success_response

router = APIRouter(prefix="/setup", tags=["Initial Setup"])


class SetupCompanyThemeResponse(BaseModel):
    primary_color: str
    secondary_color: str


class SetupCompanyBrandingResponse(BaseModel):
    id: str
    company_name: str
    logo_url: str | None = None
    theme: SetupCompanyThemeResponse


class SetupStatusResponse(BaseModel):
    step: Literal["company", "employee", "login"]
    company_id: str | None = None
    setup_required: bool
    company: SetupCompanyBrandingResponse | None = None


class InitialCompanyResponse(BaseModel):
    company: CompanyResponse
    setup_token: str


class InitialEmployeeRequest(BaseModel):
    employee_id: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    photo_url: str | None = Field(default=None, max_length=3_000_000)
    name: str = Field(min_length=2, max_length=120)
    gender: Literal["male", "female", "non_binary", "prefer_not_to_say"] = "prefer_not_to_say"
    email: EmailStr
    phone: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")
    address: AddressPayload
    designation: str = Field(min_length=2, max_length=100)
    username: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9._-]+$")
    password: str = Field(min_length=12, max_length=128)
    salary: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)
    joining_date: date = Field(default_factory=date.today)

    @field_validator("employee_id", mode="before")
    @classmethod
    def normalize_employee_id(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("photo_url", mode="before")
    @classmethod
    def normalize_photo(cls, value: str | None) -> str | None:
        return validate_image_reference(value, label="Employee photo")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: str) -> str | None:
        return normalize_indian_phone(value)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        requirements = (
            any(character.islower() for character in value),
            any(character.isupper() for character in value),
            any(character.isdigit() for character in value),
            any(not character.isalnum() for character in value),
        )
        if not all(requirements):
            raise ValueError("Password must include upper, lower, number, and special characters.")
        return value


def get_setup_service(
    database: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> SetupService:
    return SetupService(database)


@router.get("/status", response_model=ApiResponse[SetupStatusResponse])
async def setup_status(
    service: Annotated[SetupService, Depends(get_setup_service)],
) -> ApiResponse[SetupStatusResponse]:
    return success_response(SetupStatusResponse.model_validate(await service.status()))


@router.post("/company", response_model=ApiResponse[InitialCompanyResponse], status_code=status.HTTP_201_CREATED)
async def create_initial_company(
    payload: CompanyCreate,
    service: Annotated[SetupService, Depends(get_setup_service)],
) -> ApiResponse[InitialCompanyResponse]:
    company, setup_token = await service.create_initial_company(payload.model_dump(mode="json"))
    return success_response(
        InitialCompanyResponse(company=CompanyResponse.model_validate(company), setup_token=setup_token),
        message="Company created. Create the initial employee account next.",
    )


@router.post("/employee", response_model=ApiResponse[None], status_code=status.HTTP_201_CREATED)
async def create_initial_employee(
    payload: InitialEmployeeRequest,
    company_id: Annotated[str, Header(alias="X-Setup-Company-ID")],
    setup_token: Annotated[str, Header(alias="X-Setup-Token", min_length=20)],
    service: Annotated[SetupService, Depends(get_setup_service)],
) -> ApiResponse[None]:
    await service.create_initial_employee(company_id, setup_token, payload.model_dump(mode="python"))
    return success_response(message="Initial employee account created. Please sign in.")
