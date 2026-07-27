from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import BytesIO
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.application.employees.exports import create_employee_pdf, create_excel_csv
from app.application.employees.service import EmployeeService
from app.core.authorization import require_permissions
from app.core.security import Principal
from app.core.tenant import company_context
from app.infrastructure.database.mongodb import get_database
from app.shared.image_data import validate_image_reference
from app.shared.pagination import Page, PaginationParams
from app.shared.phone import normalize_indian_phone
from app.shared.response import ApiResponse, success_response

router = APIRouter(prefix="/employees", tags=["Employee Management"], dependencies=[Depends(company_context)])


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


class PasswordPayload(BaseModel):
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        requirements = (
            any(char.islower() for char in value),
            any(char.isupper() for char in value),
            any(char.isdigit() for char in value),
            any(not char.isalnum() for char in value),
        )
        if not all(requirements):
            raise ValueError("Password must include upper, lower, number, and special characters.")
        return value


class EmployeeBase(BaseModel):
    employee_id: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    photo_url: str | None = Field(default=None, max_length=3_000_000)
    name: str = Field(min_length=2, max_length=120)
    gender: Literal["male", "female", "non_binary", "prefer_not_to_say"]
    email: EmailStr
    phone: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$")
    address: AddressPayload
    designation: str = Field(min_length=2, max_length=100)
    username: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9._-]+$")
    role_id: str
    salary: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    joining_date: date
    parking_location_id: str | None = None
    status: Literal["active", "on_leave", "inactive"] = "active"

    @field_validator("employee_id", mode="before")
    @classmethod
    def normalize_employee_id(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("photo_url", mode="before")
    @classmethod
    def normalize_blank_photo_url(cls, value: str | None) -> str | None:
        return validate_image_reference(value, label="Employee photo")

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: str) -> str | None:
        return normalize_indian_phone(value)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.lower()


class EmployeeCreate(EmployeeBase, PasswordPayload):
    pass


class EmployeeUpdate(BaseModel):
    employee_id: str | None = Field(default=None, min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    photo_url: str | None = Field(default=None, max_length=3_000_000)
    name: str | None = Field(default=None, min_length=2, max_length=120)
    gender: Literal["male", "female", "non_binary", "prefer_not_to_say"] | None = None
    email: EmailStr | None = None
    phone: str | None = Field(default=None, pattern=r"^\+[1-9][0-9]{7,14}$")
    address: AddressPayload | None = None
    designation: str | None = Field(default=None, min_length=2, max_length=100)
    username: str | None = Field(default=None, min_length=3, max_length=40, pattern=r"^[A-Za-z0-9._-]+$")
    password: str | None = Field(default=None, min_length=12, max_length=128)
    role_id: str | None = None
    salary: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    joining_date: date | None = None
    parking_location_id: str | None = None
    status: Literal["active", "on_leave", "inactive"] | None = None

    @field_validator("employee_id", mode="before")
    @classmethod
    def normalize_updated_employee_id(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value

    @field_validator("photo_url", mode="before")
    @classmethod
    def normalize_updated_photo_url(cls, value: str | None) -> str | None:
        return validate_image_reference(value, label="Employee photo")

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_updated_phone(cls, value: str | None) -> str | None:
        return normalize_indian_phone(value)

    @field_validator("username")
    @classmethod
    def normalize_updated_username(cls, value: str | None) -> str | None:
        return value.lower() if value else value

    @field_validator("password")
    @classmethod
    def strong_updated_password(cls, value: str | None) -> str | None:
        if value is None:
            return value
        requirements = (
            any(char.islower() for char in value),
            any(char.isupper() for char in value),
            any(char.isdigit() for char in value),
            any(not char.isalnum() for char in value),
        )
        if not all(requirements):
            raise ValueError("Password must include upper, lower, number, and special characters.")
        return value

    @model_validator(mode="after")
    def fields_present(self) -> EmployeeUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        return self


class EmployeeResponse(EmployeeBase):
    id: str
    role_name: str
    parking_location_name: str | None


class EmployeeOptions(BaseModel):
    roles: list[dict[str, str]]
    parking_locations: list[dict[str, str]]


def get_employee_service(
    database: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> EmployeeService:
    return EmployeeService(database)


def filters(
    search: str | None = Query(default=None, max_length=100),
    employee_status: Literal["active", "on_leave", "inactive"] | None = Query(default=None, alias="status"),
    gender: Literal["male", "female", "non_binary", "prefer_not_to_say"] | None = None,
    role_id: str | None = None,
    parking_location_id: str | None = None,
    sort_by: Literal["employee_id", "name", "joining_date", "salary", "designation", "created_at"] = "name",
    sort_order: Literal["asc", "desc"] = "asc",
) -> dict[str, str | None]:
    return {
        "search": search,
        "status": employee_status,
        "gender": gender,
        "role_id": role_id,
        "parking_location_id": parking_location_id,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }


@router.get("/options", response_model=ApiResponse[EmployeeOptions])
async def employee_options(
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[EmployeeService, Depends(get_employee_service)],
    _: Annotated[Principal, Depends(require_permissions("employee:show"))],
) -> ApiResponse[EmployeeOptions]:
    return success_response(EmployeeOptions.model_validate(await service.options(company_id)))


@router.get("/export/excel")
async def export_excel(
    company_id: Annotated[str, Depends(company_context)],
    active_filters: Annotated[dict[str, str | None], Depends(filters)],
    service: Annotated[EmployeeService, Depends(get_employee_service)],
    _: Annotated[Principal, Depends(require_permissions("employee:details"))],
) -> Response:
    content = create_excel_csv(await service.export_rows(company_id, active_filters))
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=employees.csv"},
    )


@router.get("/export/pdf")
async def export_pdf(
    company_id: Annotated[str, Depends(company_context)],
    active_filters: Annotated[dict[str, str | None], Depends(filters)],
    service: Annotated[EmployeeService, Depends(get_employee_service)],
    _: Annotated[Principal, Depends(require_permissions("employee:details"))],
) -> StreamingResponse:
    content = create_employee_pdf(await service.export_rows(company_id, active_filters))
    return StreamingResponse(
        BytesIO(content),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=employees.pdf"},
    )


@router.get("", response_model=ApiResponse[Page[EmployeeResponse]])
async def list_employees(
    company_id: Annotated[str, Depends(company_context)],
    pagination: Annotated[PaginationParams, Depends()],
    active_filters: Annotated[dict[str, str | None], Depends(filters)],
    service: Annotated[EmployeeService, Depends(get_employee_service)],
    _: Annotated[Principal, Depends(require_permissions("employee:show"))],
) -> ApiResponse[Page[EmployeeResponse]]:
    page = await service.list(company_id, pagination, active_filters)
    return success_response(Page[EmployeeResponse].model_validate(page))


@router.post("", response_model=ApiResponse[EmployeeResponse], status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreate,
    company_id: Annotated[str, Depends(company_context)],
    principal: Annotated[Principal, Depends(require_permissions("employee:save"))],
    service: Annotated[EmployeeService, Depends(get_employee_service)],
) -> ApiResponse[EmployeeResponse]:
    employee = await service.create(company_id, payload.model_dump(mode="python"), principal.user_id)
    return success_response(EmployeeResponse.model_validate(employee), message="Employee created successfully.")


@router.get("/{employee_id}", response_model=ApiResponse[EmployeeResponse])
async def get_employee(
    employee_id: str,
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[EmployeeService, Depends(get_employee_service)],
    _: Annotated[Principal, Depends(require_permissions("employee:details"))],
) -> ApiResponse[EmployeeResponse]:
    return success_response(EmployeeResponse.model_validate(await service.get(company_id, employee_id)))


@router.patch("/{employee_id}", response_model=ApiResponse[EmployeeResponse])
async def update_employee(
    employee_id: str,
    payload: EmployeeUpdate,
    company_id: Annotated[str, Depends(company_context)],
    principal: Annotated[Principal, Depends(require_permissions("employee:edit"))],
    service: Annotated[EmployeeService, Depends(get_employee_service)],
) -> ApiResponse[EmployeeResponse]:
    employee = await service.update(
        company_id,
        employee_id,
        payload.model_dump(exclude_unset=True, mode="python"),
        principal.user_id,
    )
    return success_response(EmployeeResponse.model_validate(employee), message="Employee updated successfully.")


@router.delete("/{employee_id}", response_model=ApiResponse[None])
async def delete_employee(
    employee_id: str,
    company_id: Annotated[str, Depends(company_context)],
    principal: Annotated[Principal, Depends(require_permissions("employee:delete"))],
    service: Annotated[EmployeeService, Depends(get_employee_service)],
) -> ApiResponse[None]:
    await service.deactivate(company_id, employee_id, principal.user_id)
    return success_response(message="Employee deactivated successfully.")
