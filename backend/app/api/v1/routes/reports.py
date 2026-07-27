from __future__ import annotations

from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.v1.schemas.reports import (
    AuditReportRow,
    CancelledReceiptReportRow,
    DailyCollectionReportRow,
    EmployeeCollectionReportRow,
    ExportFormat,
    GstReportRow,
    MonthlyCollectionReportRow,
    PaymentReportRow,
    ReportFilters,
    ReportName,
    ReportSummaryResponse,
    VehicleReportRow,
)
from app.application.reports.exports import create_report_csv, create_report_pdf
from app.application.reports.service import ReportService
from app.core.authorization import require_permissions
from app.core.security import Principal
from app.core.tenant import company_context
from app.infrastructure.database.mongodb import get_database
from app.shared.pagination import Page, PaginationParams
from app.shared.response import ApiResponse, success_response

router = APIRouter(prefix="/reports", tags=["Reports"], dependencies=[Depends(company_context)])

EXPORT_COLUMNS: dict[ReportName, list[tuple[str, str]]] = {
    "daily-collection": [
        ("Date", "period"),
        ("Settlement collection", "settlement_collection"),
        ("Advance collection", "advance_collection"),
        ("Total collection", "total_collection"),
        ("Exit revenue", "exit_revenue"),
        ("GST", "gst_amount"),
        ("Completed exits", "exit_count"),
    ],
    "monthly-collection": [
        ("Month", "period"),
        ("Settlement collection", "settlement_collection"),
        ("Advance collection", "advance_collection"),
        ("Total collection", "total_collection"),
        ("Exit revenue", "exit_revenue"),
        ("GST", "gst_amount"),
        ("Completed exits", "exit_count"),
    ],
    "vehicle": [
        ("Vehicle number", "vehicle_number"),
        ("Vehicle type", "vehicle_type"),
        ("Token", "token_number"),
        ("Parking number", "parking_number"),
        ("Entry", "entry_at"),
        ("Exit", "exit_at"),
        ("Duration (minutes)", "duration_minutes"),
        ("Parking charge", "parking_charge"),
        ("GST", "gst_amount"),
        ("Total", "total_amount"),
        ("Advance", "advance_applied"),
        ("Settlement", "paid_amount"),
        ("Payment method", "payment_method"),
        ("Location", "location_name"),
    ],
    "employee-collection": [
        ("Employee ID", "employee_id"),
        ("Employee", "employee_name"),
        ("Designation", "designation"),
        ("Completed exits", "exits_completed"),
        ("Settlement collection", "settlement_collection"),
        ("Advance applied", "advance_applied"),
        ("Total revenue", "total_revenue"),
        ("GST", "gst_amount"),
    ],
    "gst": [
        ("Date", "period"),
        ("Parking charge", "parking_charge"),
        ("GST", "gst_amount"),
        ("Gross total", "total_amount"),
        ("Completed exits", "exits_completed"),
    ],
    "audit": [
        ("When", "occurred_at"),
        ("Actor", "actor_name"),
        ("Action", "action"),
        ("Entity", "entity_type"),
        ("Entity ID", "entity_id"),
        ("Outcome", "outcome"),
        ("Details", "details"),
    ],
    "payment": [
        ("Paid at", "paid_at"),
        ("Vehicle", "vehicle_number"),
        ("Token", "token_number"),
        ("Amount", "amount"),
        ("Method", "method"),
        ("Reference", "payment_reference"),
        ("Location", "location_name"),
        ("Status", "status"),
    ],
    "cancelled-receipts": [
        ("Cancelled at", "cancelled_at"),
        ("Receipt type", "receipt_type"),
        ("Receipt number", "receipt_number"),
        ("Vehicle", "vehicle_number"),
        ("Token", "token_number"),
        ("Cancelled by", "cancelled_by_name"),
        ("Reason", "reason"),
        ("Amount", "amount"),
        ("Status", "status"),
    ],
}


def get_report_service(database: Annotated[AsyncIOMotorDatabase, Depends(get_database)]) -> ReportService:
    return ReportService(database)


@router.get("/overview", response_model=ApiResponse[ReportSummaryResponse])
async def report_overview(
    company_id: Annotated[str, Depends(company_context)],
    filters: Annotated[ReportFilters, Depends()],
    service: Annotated[ReportService, Depends(get_report_service)],
    _: Annotated[Principal, Depends(require_permissions("report:show"))],
) -> ApiResponse[ReportSummaryResponse]:
    return success_response(ReportSummaryResponse.model_validate(await service.overview(company_id, filters)))


@router.get("/daily-collection", response_model=ApiResponse[list[DailyCollectionReportRow]])
async def daily_collection_report(
    company_id: Annotated[str, Depends(company_context)],
    filters: Annotated[ReportFilters, Depends()],
    service: Annotated[ReportService, Depends(get_report_service)],
    _: Annotated[Principal, Depends(require_permissions("report:show"))],
) -> ApiResponse[list[DailyCollectionReportRow]]:
    return success_response([DailyCollectionReportRow.model_validate(row) for row in await service.daily_collection(company_id, filters)])


@router.get("/monthly-collection", response_model=ApiResponse[list[MonthlyCollectionReportRow]])
async def monthly_collection_report(
    company_id: Annotated[str, Depends(company_context)],
    filters: Annotated[ReportFilters, Depends()],
    service: Annotated[ReportService, Depends(get_report_service)],
    _: Annotated[Principal, Depends(require_permissions("report:show"))],
) -> ApiResponse[list[MonthlyCollectionReportRow]]:
    return success_response(
        [MonthlyCollectionReportRow.model_validate(row) for row in await service.monthly_collection(company_id, filters)]
    )


@router.get("/vehicles", response_model=ApiResponse[Page[VehicleReportRow]])
async def vehicle_report(
    company_id: Annotated[str, Depends(company_context)],
    filters: Annotated[ReportFilters, Depends()],
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[ReportService, Depends(get_report_service)],
    _: Annotated[Principal, Depends(require_permissions("report:show"))],
) -> ApiResponse[Page[VehicleReportRow]]:
    return success_response(Page[VehicleReportRow].model_validate(await service.vehicles(company_id, filters, pagination)))


@router.get("/employee-collection", response_model=ApiResponse[list[EmployeeCollectionReportRow]])
async def employee_collection_report(
    company_id: Annotated[str, Depends(company_context)],
    filters: Annotated[ReportFilters, Depends()],
    service: Annotated[ReportService, Depends(get_report_service)],
    _: Annotated[Principal, Depends(require_permissions("report:show"))],
) -> ApiResponse[list[EmployeeCollectionReportRow]]:
    return success_response(
        [EmployeeCollectionReportRow.model_validate(row) for row in await service.employee_collection(company_id, filters)]
    )


@router.get("/gst", response_model=ApiResponse[list[GstReportRow]])
async def gst_report(
    company_id: Annotated[str, Depends(company_context)],
    filters: Annotated[ReportFilters, Depends()],
    service: Annotated[ReportService, Depends(get_report_service)],
    _: Annotated[Principal, Depends(require_permissions("report:show"))],
) -> ApiResponse[list[GstReportRow]]:
    return success_response([GstReportRow.model_validate(row) for row in await service.gst(company_id, filters)])


@router.get("/audit", response_model=ApiResponse[Page[AuditReportRow]])
async def audit_report(
    company_id: Annotated[str, Depends(company_context)],
    filters: Annotated[ReportFilters, Depends()],
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[ReportService, Depends(get_report_service)],
    _: Annotated[Principal, Depends(require_permissions("report:show"))],
) -> ApiResponse[Page[AuditReportRow]]:
    return success_response(Page[AuditReportRow].model_validate(await service.audit(company_id, filters, pagination)))


@router.get("/payments", response_model=ApiResponse[Page[PaymentReportRow]])
async def payment_report(
    company_id: Annotated[str, Depends(company_context)],
    filters: Annotated[ReportFilters, Depends()],
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[ReportService, Depends(get_report_service)],
    _: Annotated[Principal, Depends(require_permissions("report:show"))],
) -> ApiResponse[Page[PaymentReportRow]]:
    return success_response(Page[PaymentReportRow].model_validate(await service.payments(company_id, filters, pagination)))


@router.get("/cancelled-receipts", response_model=ApiResponse[Page[CancelledReceiptReportRow]])
async def cancelled_receipts_report(
    company_id: Annotated[str, Depends(company_context)],
    filters: Annotated[ReportFilters, Depends()],
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[ReportService, Depends(get_report_service)],
    _: Annotated[Principal, Depends(require_permissions("report:show"))],
) -> ApiResponse[Page[CancelledReceiptReportRow]]:
    return success_response(
        Page[CancelledReceiptReportRow].model_validate(await service.cancelled_receipts(company_id, filters, pagination))
    )


@router.get("/export/{report_name}/{export_format}")
async def export_report(
    report_name: ReportName,
    export_format: ExportFormat,
    company_id: Annotated[str, Depends(company_context)],
    filters: Annotated[ReportFilters, Depends()],
    service: Annotated[ReportService, Depends(get_report_service)],
    _: Annotated[Principal, Depends(require_permissions("report:details"))],
) -> Response:
    rows = await service.export_rows(report_name, company_id, filters)
    columns = EXPORT_COLUMNS[report_name]
    filename = f"{report_name}-report.{'csv' if export_format == 'excel' else 'pdf'}"
    if export_format == "excel":
        return Response(
            content=create_report_csv(columns, rows),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    title = report_name.replace("-", " ").title() + " Report"
    return StreamingResponse(
        BytesIO(create_report_pdf(title, columns, rows)),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
