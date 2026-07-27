from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

from app.application.roles.service import RoleService
from app.core.authorization import require_super_admin
from app.core.security import Principal
from app.core.tenant import company_context
from app.infrastructure.database.mongodb import get_database
from app.shared.response import ApiResponse, success_response

router = APIRouter(
    prefix="/roles",
    tags=["Role Management"],
    dependencies=[Depends(company_context), Depends(require_super_admin())],
)


class PermissionResponse(BaseModel):
    key: str
    name: str
    module: str
    action: str


class RoleResponse(BaseModel):
    id: str
    company_id: str | None
    scope: str
    code: str
    name: str
    description: str | None
    is_system: bool
    status: str
    permissions: list[PermissionResponse]


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    permission_keys: list[str] = Field(min_length=1, max_length=100)

    @field_validator("permission_keys")
    @classmethod
    def unique_permissions(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("Permissions cannot be repeated.")
        return value


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    permission_keys: list[str] | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("permission_keys")
    @classmethod
    def unique_updated_permissions(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and len(set(value)) != len(value):
            raise ValueError("Permissions cannot be repeated.")
        return value


def get_role_service(
    database: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> RoleService:
    return RoleService(database)


@router.get("/permissions", response_model=ApiResponse[list[PermissionResponse]])
async def list_permissions(
    service: Annotated[RoleService, Depends(get_role_service)],
) -> ApiResponse[list[PermissionResponse]]:
    return success_response([PermissionResponse.model_validate(item) for item in await service.list_permissions()])


@router.get("", response_model=ApiResponse[list[RoleResponse]])
async def list_roles(
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[RoleService, Depends(get_role_service)],
) -> ApiResponse[list[RoleResponse]]:
    return success_response([RoleResponse.model_validate(item) for item in await service.list_roles(company_id)])


@router.post("", response_model=ApiResponse[RoleResponse], status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: RoleCreate,
    company_id: Annotated[str, Depends(company_context)],
    principal: Annotated[Principal, Depends(require_super_admin())],
    service: Annotated[RoleService, Depends(get_role_service)],
) -> ApiResponse[RoleResponse]:
    role = await service.create_role(
        company_id, payload.name, payload.description, payload.permission_keys, principal.user_id
    )
    return success_response(RoleResponse.model_validate(role), message="Role created successfully.")


@router.get("/{role_id}", response_model=ApiResponse[RoleResponse])
async def get_role(
    role_id: str,
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[RoleService, Depends(get_role_service)],
) -> ApiResponse[RoleResponse]:
    return success_response(RoleResponse.model_validate(await service.get_role(company_id, role_id)))


@router.patch("/{role_id}", response_model=ApiResponse[RoleResponse])
async def update_role(
    role_id: str,
    payload: RoleUpdate,
    company_id: Annotated[str, Depends(company_context)],
    principal: Annotated[Principal, Depends(require_super_admin())],
    service: Annotated[RoleService, Depends(get_role_service)],
) -> ApiResponse[RoleResponse]:
    role = await service.update_role(
        company_id,
        role_id,
        payload.name,
        payload.description,
        payload.permission_keys,
        principal.user_id,
    )
    return success_response(RoleResponse.model_validate(role), message="Role updated successfully.")


@router.delete("/{role_id}", response_model=ApiResponse[None])
async def delete_role(
    role_id: str,
    company_id: Annotated[str, Depends(company_context)],
    principal: Annotated[Principal, Depends(require_super_admin())],
    service: Annotated[RoleService, Depends(get_role_service)],
) -> ApiResponse[None]:
    await service.delete_role(company_id, role_id, principal.user_id)
    return success_response(message="Role deleted successfully.")
