from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import Any
from uuid import uuid4

from bson import ObjectId
from fastapi import Request
from starlette.datastructures import Headers
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.application.audit.service import AuditLogService
from app.core.config import Settings
from app.core.logging import request_id_context
from app.core.security import decode_token
from app.core.tenant import COMPANY_ID_HEADER
from app.shared.response import error_response

logger = logging.getLogger(__name__)


class AuditMiddleware:
    """Records supported write requests after they have completed without affecting the business response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH", "DELETE"}:
            await self.app(scope, receive, send)
            return
        target = self._target(scope["path"], scope["method"])
        if not target:
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        company_id = headers.get(COMPANY_ID_HEADER)
        old_value = await self._old_value(scope, company_id, target)
        body = bytearray()
        response_status: int | None = None

        async def receive_with_capture() -> Message:
            message = await receive()
            if message["type"] == "http.request" and message.get("body") and len(body) < 65_536:
                body.extend(message["body"][: 65_536 - len(body)])
            return message

        async def send_with_status(message: Message) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive_with_capture, send_with_status)
        except Exception:
            await self._record(scope, headers, company_id, target, old_value, body, 500)
            raise
        await self._record(scope, headers, company_id, target, old_value, body, response_status or 500)

    @staticmethod
    def _target(path: str, method: str) -> dict[str, str | None] | None:
        parts = [part for part in path.split("/") if part]
        if len(parts) < 3 or parts[:2] != ["api", "v1"]:
            return None
        resource = parts[2]
        action = {"POST": "create", "PUT": "update", "PATCH": "update", "DELETE": "delete"}[method]
        if resource == "auth" and len(parts) > 3:
            return {"module": "auth", "action": parts[3], "entity_type": "authentication", "collection": None, "entity_id": None}
        if resource == "companies":
            if len(parts) >= 7 and parts[4] == "branches" and parts[6] == "locations":
                return {
                    "module": "company",
                    "action": action,
                    "entity_type": "parking_location",
                    "collection": "parking_locations",
                    "entity_id": parts[7] if len(parts) > 7 else None,
                }
            if len(parts) >= 5 and parts[4] == "branches":
                return {
                    "module": "company",
                    "action": action,
                    "entity_type": "branch",
                    "collection": "branches",
                    "entity_id": parts[5] if len(parts) > 5 else None,
                }
            return {
                "module": "company",
                "action": action,
                "entity_type": "company",
                "collection": "companies",
                "entity_id": parts[3] if len(parts) > 3 else None,
            }
        targets = {
            "employees": ("employee", "employee", "employees"),
            "roles": ("role", "role", "roles"),
            "parking-rates": ("rate", "parking_rate", "parking_rates"),
        }
        if resource in targets:
            module, entity_type, collection = targets[resource]
            return {"module": module, "action": action, "entity_type": entity_type, "collection": collection, "entity_id": parts[3] if len(parts) > 3 else None}
        if resource == "vehicle-entries" and method == "POST":
            return {"module": "parking_entry", "action": "check_in", "entity_type": "vehicle_entry", "collection": None, "entity_id": None}
        if resource == "vehicle-exits" and method == "POST":
            return {"module": "parking_exit", "action": "check_out", "entity_type": "vehicle_exit", "collection": None, "entity_id": None}
        if resource == "advanced" and len(parts) > 3:
            targets = {
                "monthly-passes": ("monthly_pass", "monthly_passes"),
                "parking-slots": ("parking_slot", "parking_slots"),
                "reserved-slots": ("reserved_slot", "reserved_slots"),
            }
            if parts[3] in targets:
                entity_type, collection = targets[parts[3]]
                return {
                    "module": "advanced",
                    "action": action,
                    "entity_type": entity_type,
                    "collection": collection,
                    "entity_id": parts[4] if len(parts) > 4 else None,
                }
        if resource == "system" and method == "POST" and len(parts) > 3 and parts[3] == "restore":
            return {"module": "system", "action": "restore", "entity_type": "tenant_backup", "collection": None, "entity_id": None}
        return None

    async def _old_value(self, scope: Scope, company_id: str | None, target: dict[str, str | None]) -> dict[str, Any] | None:
        collection = target["collection"]
        entity_id = target["entity_id"]
        if not collection or not entity_id or not ObjectId.is_valid(entity_id):
            return None
        try:
            database = scope["app"].state.mongo.database
            query: dict[str, Any] = {"_id": ObjectId(entity_id)}
            if collection != "companies" and company_id and ObjectId.is_valid(company_id):
                query["company_id"] = ObjectId(company_id)
            return await database[collection].find_one(query)
        except Exception:
            logger.exception("Unable to capture the pre-change audit snapshot")
            return None

    async def _record(
        self,
        scope: Scope,
        headers: Headers,
        company_id: str | None,
        target: dict[str, str | None],
        old_value: dict[str, Any] | None,
        body: bytearray,
        response_status: int,
    ) -> None:
        if not company_id or not ObjectId.is_valid(company_id):
            return
        try:
            payload = json.loads(body.decode("utf-8")) if body and "application/json" in headers.get("content-type", "") else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = {"payload": "[unavailable]"}
        if target["module"] == "system" and target["action"] == "restore":
            payload = {"backup": "[redacted]"}
        level = "success" if response_status < 400 else "warning" if response_status < 500 else "error"
        new_value = {"status": "deleted"} if target["action"] == "delete" and level == "success" else payload
        state = scope.get("state", {})
        principal = state.get("principal")
        actor_id = getattr(principal, "user_id", None)
        client = scope.get("client")
        ip_address = client[0] if client else None
        action = target["action"] or "change"
        entity_type = target["entity_type"] or "resource"
        message = f"{entity_type.replace('_', ' ').title()} {action.replace('_', ' ')} {'completed' if level == 'success' else 'failed'}."
        database = scope["app"].state.mongo.database
        await AuditLogService(database).record(
            company_id=company_id,
            actor_id=actor_id,
            ip_address=ip_address,
            module=target["module"] or "system",
            action=action,
            entity_type=entity_type,
            entity_id=target["entity_id"],
            old_value=old_value,
            new_value=new_value,
            level=level,
            outcome="success" if level == "success" else "failure",
            message=message,
            request_id=state.get("request_id"),
        )


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Adds request correlation and latency headers for every HTTP response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        context_token = request_id_context.set(request_id)
        try:
            started = perf_counter()
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-Ms"] = f"{(perf_counter() - started) * 1000:.2f}"
            return response
        finally:
            request_id_context.reset(context_token)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Optionally resolves a Bearer token; protected routes enforce a principal via dependencies."""

    def __init__(self, app, *, settings: Settings) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.principal = None
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            try:
                request.state.principal = decode_token(token, self.settings)
            except Exception:  # Protected dependencies return a standard 401 response.
                logger.info(
                    "Authentication token could not be verified",
                    extra={"request_id": getattr(request.state, "request_id", None)},
                )
        return await call_next(request)


class CompanyContextMiddleware(BaseHTTPMiddleware):
    """Requires a tenant id on versioned API calls and exposes it to dependencies."""

    excluded_paths = {"/api/v1/system/health", "/api/v1/openapi.json"}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if (
            request.method == "OPTIONS"
            or not request.url.path.startswith("/api/v1")
            or request.url.path in self.excluded_paths
            or request.url.path.startswith("/api/v1/setup/")
            or request.url.path.startswith("/api/v1/openapi")
        ):
            return await call_next(request)
        company_id = request.headers.get(COMPANY_ID_HEADER)
        if not company_id or not ObjectId.is_valid(company_id):
            return JSONResponse(
                status_code=400,
                content=error_response(
                    code="company_context_required",
                    message="A valid X-Company-ID header is required.",
                    request_id=getattr(request.state, "request_id", None),
                ).model_dump(by_alias=True, mode="json"),
            )
        request.state.company_id = company_id
        return await call_next(request)
