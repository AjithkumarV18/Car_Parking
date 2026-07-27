from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.api.dependencies import get_request_id
from app.infrastructure.database.mongodb import get_database
from app.shared.response import ApiResponse, success_response

router = APIRouter(prefix="/system", tags=["System"])


class HealthStatus(BaseModel):
    status: str
    timestamp: datetime
    database: str


@router.get(
    "/health",
    response_model=ApiResponse[HealthStatus],
    status_code=status.HTTP_200_OK,
    summary="Check application and database readiness",
)
async def health_check(
    database: AsyncIOMotorDatabase = Depends(get_database),
    request_id: str | None = Depends(get_request_id),
) -> ApiResponse[HealthStatus]:
    await database.command("ping")
    return success_response(
        HealthStatus(status="healthy", timestamp=datetime.now(UTC), database="connected"),
        request_id=request_id,
    )
