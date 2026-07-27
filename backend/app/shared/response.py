from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ApiResponse(BaseModel, Generic[DataT]):
    """Canonical successful or failed API envelope."""

    success: bool
    message: str = "OK"
    data: DataT | None = None
    error: ErrorDetail | None = None
    request_id: str | None = Field(default=None, serialization_alias="requestId")


def success_response(
    data: DataT | None = None,
    *,
    message: str = "OK",
    request_id: str | None = None,
) -> ApiResponse[DataT]:
    return ApiResponse(success=True, message=message, data=data, request_id=request_id)


def error_response(
    *,
    code: str,
    message: str,
    details: Any | None = None,
    request_id: str | None = None,
) -> ApiResponse[None]:
    return ApiResponse(
        success=False,
        message=message,
        error=ErrorDetail(code=code, message=message, details=details),
        request_id=request_id,
    )
