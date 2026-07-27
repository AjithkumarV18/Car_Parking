from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from bson import ObjectId
from pydantic import BaseModel, Field, field_validator, model_validator


class AuditLogFilters(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    module: str | None = Field(default=None, max_length=64)
    action: str | None = Field(default=None, max_length=64)
    level: Literal["success", "warning", "error"] | None = None
    user_id: str | None = None
    search: str | None = Field(default=None, max_length=100)

    @field_validator("module", "action", "search")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip()
        if not ObjectId.is_valid(normalized):
            raise ValueError("User ID must be a valid 24-character identifier.")
        return normalized

    @model_validator(mode="after")
    def validate_date_range(self) -> AuditLogFilters:
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("Date from must be on or before date to.")
        if self.date_from and self.date_to and (self.date_to - self.date_from).days > 366:
            raise ValueError("Audit date range cannot exceed 366 days.")
        return self


class AuditActorResponse(BaseModel):
    id: str | None
    name: str
    email: str | None = None


class AuditLogResponse(BaseModel):
    id: str
    actor: AuditActorResponse
    ip_address: str | None
    module: str
    action: str
    entity_type: str
    entity_id: str | None
    old_value: dict[str, Any] | list[Any] | str | None
    new_value: dict[str, Any] | list[Any] | str | None
    level: Literal["success", "warning", "error"]
    outcome: Literal["success", "failure"]
    message: str
    request_id: str | None
    occurred_at: datetime
    date: date
    time: str


class AuditTimelineResponse(BaseModel):
    id: str
    actor: AuditActorResponse
    ip_address: str | None
    module: str
    action: str
    entity_type: str
    entity_id: str | None
    level: Literal["success", "warning", "error"]
    message: str
    occurred_at: datetime
    date: date
    time: str
