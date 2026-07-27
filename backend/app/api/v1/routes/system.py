from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.application.system.service import TenantBackupService
from app.core.authorization import require_super_admin
from app.core.security import Principal
from app.core.tenant import company_context
from app.infrastructure.database.mongodb import get_database
from app.shared.response import ApiResponse, success_response

router = APIRouter(
    prefix="/system",
    tags=["System Maintenance"],
    dependencies=[Depends(company_context), Depends(require_super_admin())],
)


class RestoreRequest(BaseModel):
    backup_json: str = Field(min_length=2, max_length=25_000_000)


def service(database: Annotated[AsyncIOMotorDatabase, Depends(get_database)]) -> TenantBackupService:
    return TenantBackupService(database)


@router.get("/backup", response_class=Response)
async def download_backup(
    company_id: Annotated[str, Depends(company_context)],
    _: Annotated[Principal, Depends(require_super_admin())],
    svc: Annotated[TenantBackupService, Depends(service)],
) -> Response:
    backup = await svc.export(company_id)
    return Response(
        content=backup,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="parking-tenant-backup.json"'},
    )


@router.post("/restore", response_model=ApiResponse[dict[str, int]])
async def restore_backup(
    payload: RestoreRequest,
    company_id: Annotated[str, Depends(company_context)],
    _: Annotated[Principal, Depends(require_super_admin())],
    svc: Annotated[TenantBackupService, Depends(service)],
) -> ApiResponse[dict[str, int]]:
    return success_response(await svc.restore(company_id, payload.backup_json), message="Backup merge restore completed.")
