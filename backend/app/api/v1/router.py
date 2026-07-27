from fastapi import APIRouter

from app.api.v1.routes import (
    advanced,
    audit_logs,
    auth,
    companies,
    dashboard,
    employees,
    health,
    rates,
    reports,
    roles,
    settings,
    setup,
    system,
    vehicle_entries,
    vehicle_exits,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(setup.router)
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(reports.router)
api_router.include_router(audit_logs.router)
api_router.include_router(advanced.router)
api_router.include_router(settings.router)
api_router.include_router(system.router)
api_router.include_router(companies.router)
api_router.include_router(roles.router)
api_router.include_router(employees.router)
api_router.include_router(rates.router)
api_router.include_router(vehicle_entries.router)
api_router.include_router(vehicle_exits.router)
