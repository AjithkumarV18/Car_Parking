from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.v1.schemas.dashboard import DashboardOverviewResponse
from app.application.dashboard.service import DashboardService
from app.core.authorization import require_permissions
from app.core.security import Principal
from app.core.tenant import company_context
from app.infrastructure.database.mongodb import get_database
from app.shared.response import ApiResponse, success_response

router = APIRouter(prefix="/dashboard", tags=["Dashboard"], dependencies=[Depends(company_context)])


def get_dashboard_service(database: Annotated[AsyncIOMotorDatabase, Depends(get_database)]) -> DashboardService:
    return DashboardService(database)


@router.get("/overview", response_model=ApiResponse[DashboardOverviewResponse])
async def dashboard_overview(
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
    _: Annotated[Principal, Depends(require_permissions("dashboard:show"))],
) -> ApiResponse[DashboardOverviewResponse]:
    overview = await service.overview(company_id)
    return success_response(DashboardOverviewResponse.model_validate(overview))
