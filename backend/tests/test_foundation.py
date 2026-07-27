from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.api.v1.routes.companies import BranchCreate, CompanyCreate
from app.api.v1.routes.employees import EmployeeCreate
from app.api.v1.routes.rates import ParkingRateCreate
from app.api.v1.routes.settings import SoftwareSettingsUpdate
from app.api.v1.routes.setup import SetupStatusResponse
from app.api.v1.schemas.advanced import MonthlyPassCreate
from app.api.v1.schemas.parking import VehicleEntryCreate, VehicleExitCreate
from app.api.v1.schemas.reports import ReportFilters
from app.application.employees.exports import create_employee_pdf, create_excel_csv
from app.application.parking.service import ParkingOperationsService
from app.application.reports.service import MAX_EXPORT_ROWS, ReportService
from app.core.config import Settings
from app.core.constants import TokenType
from app.core.security import create_token, decode_token
from app.main import app
from app.shared.pagination import PaginationParams


def test_jwt_round_trip_preserves_authorization_claims() -> None:
    settings = Settings(jwt_secret_key="test-secret-that-is-long-enough-for-any-environment")
    token = create_token(
        subject="test-user",
        company_id="507f1f77bcf86cd799439011",
        roles={"admin"},
        permissions={"system:read"},
        token_type=TokenType.ACCESS,
        settings=settings,
    )

    principal = decode_token(token, settings)

    assert principal.user_id == "test-user"
    assert principal.company_id == "507f1f77bcf86cd799439011"
    assert principal.roles == {"admin"}
    assert principal.permissions == {"system:read"}


def test_openapi_exposes_health_and_bearer_auth_scheme() -> None:
    schema = app.openapi()

    assert "/api/v1/system/health" in schema["paths"]
    assert schema["components"]["securitySchemes"]["bearerAuth"]["scheme"] == "bearer"
    company_endpoint = schema["paths"]["/api/v1/companies"]["get"]
    assert company_endpoint["security"] == [{"bearerAuth": []}]
    assert any(parameter["name"] == "X-Company-ID" for parameter in company_endpoint["parameters"])
    assert "post" not in schema["paths"]["/api/v1/companies"]
    assert "delete" not in schema["paths"]["/api/v1/companies/{company_id}"]
    entry_endpoint = schema["paths"]["/api/v1/vehicle-entries"]["post"]
    assert entry_endpoint["security"] == [{"bearerAuth": []}]
    assert any(parameter["name"] == "X-Company-ID" for parameter in entry_endpoint["parameters"])
    assert "/api/v1/vehicle-exits/{entry_id}/calculate" in schema["paths"]
    assert "/api/v1/vehicle-entries/membership" in schema["paths"]
    assert "/api/v1/setup/status" in schema["paths"]
    assert "/api/v1/setup/company" in schema["paths"]
    assert "security" not in schema["paths"]["/api/v1/setup/status"]["get"]
    open_entries_endpoint = schema["paths"]["/api/v1/vehicle-exits/open-entries"]["get"]
    assert open_entries_endpoint["security"] == [{"bearerAuth": []}]
    assert any(parameter["name"] == "X-Company-ID" for parameter in open_entries_endpoint["parameters"])
    settings_endpoint = schema["paths"]["/api/v1/settings/software"]["get"]
    assert settings_endpoint["security"] == [{"bearerAuth": []}]
    assert any(parameter["name"] == "X-Company-ID" for parameter in settings_endpoint["parameters"])


def test_setup_status_exposes_only_public_company_branding() -> None:
    status = SetupStatusResponse.model_validate(
        {
            "step": "login",
            "company_id": "507f1f77bcf86cd799439011",
            "setup_required": False,
            "company": {
                "id": "507f1f77bcf86cd799439011",
                "company_name": "AK Smart Parking",
                "logo_url": "data:image/png;base64,aGVsbG8=",
                "theme": {"primary_color": "#123456", "secondary_color": "#ABCDEF"},
            },
        }
    )
    assert status.company is not None
    assert status.company.company_name == "AK Smart Parking"
    assert status.company.theme.primary_color == "#123456"


def test_software_settings_update_rejects_empty_and_unknown_values() -> None:
    assert SoftwareSettingsUpdate(rfid_entry_enabled=False).rfid_entry_enabled is False
    with pytest.raises(ValidationError):
        SoftwareSettingsUpdate()
    with pytest.raises(ValidationError):
        SoftwareSettingsUpdate(unsupported_feature=True)


def test_company_payload_validates_gstin_phone_and_theme() -> None:
    company = CompanyCreate(
        company_name="Acme Logistics",
        address={
            "line1": "42 Logistics Road",
            "city": "Bengaluru",
            "state": "Karnataka",
            "postal_code": "560001",
        },
        gstin="29ABCDE1234F1Z5",
        phone="+919999999999",
        email="ops@acme.example",
    )
    assert company.currency == "INR"
    with pytest.raises(ValidationError):
        CompanyCreate(
            company_name="Invalid company",
            address={
                "line1": "42 Logistics Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "postal_code": "560001",
            },
            gstin="not-a-gstin",
            phone="not-a-phone",
            email="ops@acme.example",
        )


def test_optional_company_and_branch_contacts_accept_blank_form_values() -> None:
    address = {
        "line1": "42 Logistics Road",
        "city": "Bengaluru",
        "state": "Karnataka",
        "postal_code": "560001",
    }
    company = CompanyCreate(
        company_name="Optional logo company",
        address=address,
        phone="+919999999999",
        email="ops@acme.example",
        logo_url="",
    )
    branch = BranchCreate(name="Central branch", address=address, phone="", email="")
    assert company.logo_url is None
    assert branch.phone is None
    assert branch.email is None


def test_company_and_employee_accept_uploaded_image_data() -> None:
    image = "data:image/png;base64,aGVsbG8="
    company = CompanyCreate(
        company_name="Image company",
        address={"line1": "42 Logistics Road", "city": "Bengaluru", "state": "Karnataka", "postal_code": "560001"},
        phone="9876543210",
        email="ops@acme.example",
        logo_url=image,
    )
    employee = EmployeeCreate(
        employee_id="EMP-001",
        photo_url=image,
        name="Asha Rao",
        gender="female",
        email="asha@example.com",
        phone="9876543210",
        address={"line1": "42 Logistics Road", "city": "Bengaluru", "state": "Karnataka", "postal_code": "560001"},
        designation="Attendant",
        username="asha.rao",
        password="StrongPass123!",
        role_id="507f1f77bcf86cd799439011",
        salary="45000.00",
        joining_date="2026-07-27",
    )
    assert company.logo_url == image
    assert employee.photo_url == image
    with pytest.raises(ValidationError):
        CompanyCreate(
            company_name="Invalid image company",
            address={"line1": "42 Logistics Road", "city": "Bengaluru", "state": "Karnataka", "postal_code": "560001"},
            phone="9876543210",
            email="ops@example.com",
            logo_url="not-an-image",
        )


def test_company_accepts_a_standard_indian_phone_number() -> None:
    company = CompanyCreate(
        company_name="Indian phone company",
        address={"line1": "42 Logistics Road", "city": "Bengaluru", "state": "Karnataka", "postal_code": "560001"},
        phone="9876543210",
        email="ops@acme.example",
    )
    assert company.phone == "+919876543210"


def test_employee_accepts_standard_indian_phone_and_normalizes_employee_id() -> None:
    employee = EmployeeCreate(
        employee_id=" emp-001 ",
        name="Asha Rao",
        gender="female",
        email="asha@example.com",
        phone="9876543210",
        address={"line1": "42 Logistics Road", "city": "Bengaluru", "state": "Karnataka", "postal_code": "560001"},
        designation="Attendant",
        username="asha.rao",
        password="StrongPass123!",
        role_id="507f1f77bcf86cd799439011",
        salary="45000.00",
        joining_date="2026-07-27",
    )
    assert employee.employee_id == "EMP-001"
    assert employee.phone == "+919876543210"


def test_monthly_pass_accepts_a_standard_indian_mobile_number() -> None:
    monthly_pass = MonthlyPassCreate(
        vehicle_number="TN01AB1818",
        vehicle_type="car",
        holder_name="Ajith Kumar",
        mobile="9876543210",
        valid_from="2026-07-27",
        valid_until="2026-08-27",
        amount="2500.00",
    )
    assert monthly_pass.mobile == "+919876543210"


def test_employee_exports_create_excel_compatible_csv_and_pdf() -> None:
    rows = [
        {
            "employee_id": "EMP-001",
            "name": "Asha Rao",
            "gender": "female",
            "email": "asha@example.com",
            "phone": "+919999999999",
            "designation": "Attendant",
            "role_name": "Employee",
            "parking_location_name": "North Yard",
            "salary": "45000.00",
            "joining_date": "2026-07-26",
            "status": "active",
        }
    ]
    assert "Employee ID" in create_excel_csv(rows).decode("utf-8-sig")
    assert create_employee_pdf(rows).startswith(b"%PDF")


async def test_report_export_uses_the_internal_export_page_limit() -> None:
    class ExportProbe(ReportService):
        captured_limit: int | None = None

        async def _vehicles(self, company_id: str, filters: ReportFilters, pagination: PaginationParams) -> dict[str, list[object]]:
            self.captured_limit = pagination.limit
            return {"items": []}

    service = ExportProbe(None)

    assert await service._export_rows("vehicle", "507f1f77bcf86cd799439011", ReportFilters()) == []
    assert service.captured_limit == MAX_EXPORT_ROWS


def test_parking_rate_payload_requires_contiguous_slabs() -> None:
    rate = ParkingRateCreate(
        vehicle_type="truck",
        effective_date="2026-08-01",
        duration_slabs=[
            {"from_minutes": 0, "to_minutes": 60, "amount": "120.00", "gst_percent": "18.00"},
            {"from_minutes": 60, "to_minutes": None, "amount": "650.00", "gst_percent": "18.00"},
        ],
    )
    assert rate.vehicle_type == "truck"
    with pytest.raises(ValidationError):
        ParkingRateCreate(
            vehicle_type="truck",
            effective_date="2026-08-01",
            duration_slabs=[
                {"from_minutes": 0, "to_minutes": 60, "amount": "120.00", "gst_percent": "18.00"},
                {"from_minutes": 90, "to_minutes": None, "amount": "650.00", "gst_percent": "18.00"},
            ],
        )


def test_vehicle_entry_and_exit_contracts_apply_operator_validation() -> None:
    entry = VehicleEntryCreate(vehicle_number="ka 01-ab 1234", vehicle_type="car", advance_amount="20.00")
    assert entry.vehicle_number == "KA01AB1234"
    with pytest.raises(ValidationError):
        VehicleExitCreate(entry_id="507f1f77bcf86cd799439011", paid_amount="10.00")
    exit_payload = VehicleExitCreate(entry_id="507f1f77bcf86cd799439011", paid_amount="10.00", payment_method="cash")
    assert exit_payload.payment_method == "cash"

    service = ParkingOperationsService(None)
    now = datetime.now(UTC)
    calculation = service._calculation_for_entry(
        {
            # MongoDB clients configured without tz_aware historically return naive UTC values.
            "entry_at": (now - timedelta(minutes=75)).replace(tzinfo=None),
            "advance_amount": "20.00",
            "rate_snapshot": {
                "effective_date": now,
                "duration_slabs": [
                    {"from_minutes": 0, "to_minutes": 60, "amount": "30.00", "gst_percent": "18.00"},
                    {"from_minutes": 60, "to_minutes": None, "amount": "50.00", "gst_percent": "18.00"},
                ],
            },
        },
        now,
    )
    assert calculation["duration_minutes"] == 75
    assert str(calculation["total_amount"]) == "59.00"
    assert str(calculation["balance_amount"]) == "39.00"
