from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.application.auth.service import AuthService
from app.core.authorization import get_current_principal
from app.core.config import Settings, get_settings
from app.core.security import Principal
from app.core.tenant import company_context
from app.infrastructure.database.mongodb import get_database
from app.shared.response import ApiResponse, success_response

router = APIRouter(prefix="/auth", tags=["Authentication"])


class PasswordPayload(BaseModel):
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def enforce_password_strength(cls, value: str) -> str:
        requirements = (
            any(char.islower() for char in value),
            any(char.isupper() for char in value),
            any(char.isdigit() for char in value),
            any(not char.isalnum() for char in value),
        )
        if not all(requirements):
            raise ValueError("Password must include upper, lower, number, and special characters.")
        return value


class RegisterRequest(PasswordPayload):
    email: EmailStr
    display_name: str = Field(min_length=2, max_length=120)
    remember_me: bool = False


class LoginRequest(PasswordPayload):
    email: EmailStr
    remember_me: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(PasswordPayload):
    token: str = Field(min_length=20)


class CompanyThemeResponse(BaseModel):
    primary_color: str
    secondary_color: str


class AuthenticatedUserResponse(BaseModel):
    id: str
    company_id: str
    email: EmailStr
    display_name: str
    username: str | None = None
    photo_url: str | None = None
    company_name: str | None = None
    company_logo_url: str | None = None
    company_theme: CompanyThemeResponse | None = None
    roles: list[str]
    permissions: list[str]
    is_super_admin: bool


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: AuthenticatedUserResponse


class ForgotPasswordResponse(BaseModel):
    message: str
    debug_reset_token: str | None = None


def get_auth_service(
    database: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    return AuthService(database, settings)


@router.post("/register", response_model=ApiResponse[TokenPairResponse], status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[TokenPairResponse]:
    tokens = await service.register(
        company_id,
        email=str(payload.email),
        password=payload.password,
        display_name=payload.display_name,
        remember_me=payload.remember_me,
    )
    return success_response(TokenPairResponse.model_validate(tokens), message="Account registered successfully.")


@router.post("/login", response_model=ApiResponse[TokenPairResponse])
async def login(
    payload: LoginRequest,
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[TokenPairResponse]:
    tokens = await service.login(
        company_id,
        email=str(payload.email),
        password=payload.password,
        remember_me=payload.remember_me,
    )
    return success_response(TokenPairResponse.model_validate(tokens), message="Login successful.")


@router.post("/refresh", response_model=ApiResponse[TokenPairResponse])
async def refresh(
    payload: RefreshRequest,
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[TokenPairResponse]:
    tokens = await service.refresh(company_id, payload.refresh_token)
    return success_response(TokenPairResponse.model_validate(tokens), message="Token refreshed successfully.")


@router.post("/forgot-password", response_model=ApiResponse[ForgotPasswordResponse])
async def forgot_password(
    payload: ForgotPasswordRequest,
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ApiResponse[ForgotPasswordResponse]:
    token = await service.request_password_reset(company_id, str(payload.email))
    response = ForgotPasswordResponse(
        message="If an active account exists, password reset instructions have been queued.",
        debug_reset_token=token if settings.debug else None,
    )
    return success_response(response)


@router.post("/reset-password", response_model=ApiResponse[None])
async def reset_password(
    payload: ResetPasswordRequest,
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[None]:
    await service.reset_password(company_id, payload.token, payload.password)
    return success_response(message="Password reset successfully. Please sign in again.")


@router.get("/me", response_model=ApiResponse[AuthenticatedUserResponse])
async def current_user(
    principal: Annotated[Principal, Depends(get_current_principal)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[AuthenticatedUserResponse]:
    user = await service.get_profile(principal.user_id, principal.company_id)
    return success_response(AuthenticatedUserResponse.model_validate(user))
