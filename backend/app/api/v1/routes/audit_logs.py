from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.v1.schemas.audit import AuditLogFilters, AuditLogResponse, AuditTimelineResponse
from app.application.audit.service import AuditLogService
from app.core.authorization import require_permissions
from app.core.security import Principal
from app.core.tenant import company_context
from app.infrastructure.database.mongodb import get_database
from app.shared.pagination import Page, PaginationParams
from app.shared.response import ApiResponse, success_response

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"], dependencies=[Depends(company_context)])


def get_audit_log_service(database: Annotated[AsyncIOMotorDatabase, Depends(get_database)]) -> AuditLogService:
    return AuditLogService(database)


@router.get("", response_model=ApiResponse[Page[AuditTimelineResponse]])
async def list_audit_logs(
    company_id: Annotated[str, Depends(company_context)],
    filters: Annotated[AuditLogFilters, Depends()],
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[AuditLogService, Depends(get_audit_log_service)],
    _: Annotated[Principal, Depends(require_permissions("audit:show"))],
) -> ApiResponse[Page[AuditTimelineResponse]]:
    return success_response(Page[AuditTimelineResponse].model_validate(await service.list(company_id, filters, pagination)))


@router.get("/timeline", response_model=ApiResponse[list[AuditTimelineResponse]])
async def audit_timeline(
    company_id: Annotated[str, Depends(company_context)],
    filters: Annotated[AuditLogFilters, Depends()],
    service: Annotated[AuditLogService, Depends(get_audit_log_service)],
    _: Annotated[Principal, Depends(require_permissions("audit:show"))],
    limit: int = Query(default=30, ge=1, le=100),
) -> ApiResponse[list[AuditTimelineResponse]]:
    return success_response([AuditTimelineResponse.model_validate(item) for item in await service.timeline(company_id, filters, limit)])


@router.get("/{audit_id}", response_model=ApiResponse[AuditLogResponse])
async def audit_log_details(
    audit_id: str,
    company_id: Annotated[str, Depends(company_context)],
    service: Annotated[AuditLogService, Depends(get_audit_log_service)],
    _: Annotated[Principal, Depends(require_permissions("audit:details"))],
) -> ApiResponse[AuditLogResponse]:
    return success_response(AuditLogResponse.model_validate(await service.get(company_id, audit_id)))
