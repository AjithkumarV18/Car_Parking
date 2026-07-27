from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.api.v1.schemas.dashboard import DashboardOverviewResponse
from app.application.dashboard.service import DashboardService


def test_dashboard_contract_and_tenant_day_boundary() -> None:
    start = DashboardService._day_start(datetime(2026, 7, 26, 20, 0, tzinfo=UTC), ZoneInfo("Asia/Kolkata"))
    assert start == datetime(2026, 7, 26, 18, 30, tzinfo=UTC)

    overview = DashboardOverviewResponse(
        currency="INR",
        today_collection="100.00",
        today_entries=2,
        today_exits=1,
        monthly_revenue="900.00",
        weekly_revenue="450.00",
        occupied_slots=2,
        available_slots=8,
        revenue=[],
        vehicle_types=[],
        occupancy=[],
        recent_activities=[],
    )
    assert overview.available_slots == 8
