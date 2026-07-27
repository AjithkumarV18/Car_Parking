from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class Entity(BaseModel):
    """Minimal immutable-by-convention base for persisted domain entities."""

    id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
