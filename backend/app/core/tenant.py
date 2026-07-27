from __future__ import annotations

from typing import Annotated

from bson import ObjectId
from fastapi import Header, Request

from app.core.exceptions import AuthorizationError

COMPANY_ID_HEADER = "X-Company-ID"


def get_company_id(request: Request) -> str:
    company_id = getattr(request.state, "company_id", None)
    if not isinstance(company_id, str) or not ObjectId.is_valid(company_id):
        raise AuthorizationError("A valid X-Company-ID header is required.")
    return company_id


def company_context(
    request: Request,
    x_company_id: Annotated[str, Header(alias=COMPANY_ID_HEADER)],
) -> str:
    """Document the mandatory tenant header in OpenAPI and return its validated value."""

    company_id = get_company_id(request)
    if company_id != x_company_id:
        raise AuthorizationError("Company context mismatch.")
    return company_id
