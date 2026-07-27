from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.reports import ReportFilters, ReportSummaryResponse
from app.application.reports.exports import create_report_csv, create_report_pdf
from app.application.reports.service import ReportService
from app.main import create_application


def test_report_filters_reject_invalid_date_ranges_and_location_ids() -> None:
    with pytest.raises(ValidationError, match="Date from must be on or before"):
        ReportFilters(date_from=date(2026, 7, 27), date_to=date(2026, 7, 26))
    with pytest.raises(ValidationError, match="Location ID must be a valid"):
        ReportFilters(location_id="not-an-object-id")


def test_report_contract_and_company_local_date_boundary() -> None:
    boundary = ReportService._utc_day_boundary(date(2026, 7, 27), ZoneInfo("Asia/Kolkata"))
    assert boundary == datetime(2026, 7, 26, 18, 30, tzinfo=UTC)

    summary = ReportSummaryResponse(
        currency="INR",
        date_from=date(2026, 7, 1),
        date_to=date(2026, 7, 27),
        total_collection="500.00",
        advance_collection="100.00",
        settlement_collection="400.00",
        completed_exits=3,
        gst_collected="60.00",
        revenue=[{"period": "2026-07-27", "label": "27 Jul", "amount": "500.00"}],
        payment_methods=[
            {"method": "cash", "amount": "400.00", "count": 2},
            {"method": "upi", "amount": "0.00", "count": 0},
            {"method": "card", "amount": "0.00", "count": 0},
        ],
    )
    assert summary.completed_exits == 3


def test_report_exports_and_swagger_routes() -> None:
    rows = [{"period": "2026-07-27", "total_collection": "500.00"}]
    columns = [("Date", "period"), ("Total collection", "total_collection")]
    assert create_report_csv(columns, rows).startswith("\ufeffDate,Total collection".encode())
    assert create_report_pdf("Daily Collection Report", columns, rows).startswith(b"%PDF")

    schema = create_application().openapi()
    assert "/api/v1/reports/overview" in schema["paths"]
    assert "/api/v1/reports/export/{report_name}/{export_format}" in schema["paths"]
