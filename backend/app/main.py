from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.errors import register_exception_handlers
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import AuditMiddleware, AuthenticationMiddleware, CompanyContextMiddleware, RequestContextMiddleware
from app.infrastructure.database.mongodb import MongoConnection
from app.infrastructure.repositories.advanced_repositories import initialize_advanced_collections
from app.infrastructure.repositories.auth_repositories import initialize_auth_collections
from app.infrastructure.repositories.company_repositories import initialize_company_collections
from app.infrastructure.repositories.employee_repositories import initialize_employee_collections
from app.infrastructure.repositories.parking_repositories import initialize_parking_collections
from app.infrastructure.repositories.rate_repositories import initialize_rate_collections
from app.infrastructure.repositories.report_repositories import initialize_report_collections
from app.infrastructure.repositories.settings_repositories import initialize_settings_collections

settings = get_settings()
configure_logging(settings)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo = MongoConnection(settings)
    await mongo.connect()
    app.state.mongo = mongo
    await initialize_auth_collections(mongo.database)
    await initialize_company_collections(mongo.database)
    await initialize_employee_collections(mongo.database)
    await initialize_rate_collections(mongo.database)
    await initialize_parking_collections(mongo.database)
    await initialize_report_collections(mongo.database)
    await initialize_settings_collections(mongo.database)
    await initialize_advanced_collections(mongo.database)
    try:
        yield
    finally:
        await mongo.close()


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        description="Foundation API for commercial vehicle parking management.",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json" if settings.docs_enabled else None,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        lifespan=lifespan,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts or ["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Company-ID", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Process-Time-Ms"],
    )
    app.add_middleware(AuthenticationMiddleware, settings=settings)
    app.add_middleware(CompanyContextMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(AuditMiddleware)

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    if STATIC_DIR.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=STATIC_DIR / "assets"),
            name="assets",
        )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_react_app(full_path: str):
        requested_file = STATIC_DIR / full_path

        if full_path and requested_file.exists() and requested_file.is_file():
            return FileResponse(requested_file)

        return FileResponse(STATIC_DIR / "index.html")

    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=settings.project_name,
            version=settings.version,
            description=app.description,
            routes=app.routes,
        )
        schema.setdefault("components", {}).setdefault("securitySchemes", {})["bearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Provide a signed access token for protected endpoints.",
        }
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
    return app


app = create_application()
