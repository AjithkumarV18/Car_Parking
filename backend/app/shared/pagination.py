from __future__ import annotations

from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, computed_field

from app.shared.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

ItemT = TypeVar("ItemT")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="One-based page number")
    limit: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)

    @computed_field
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class PageMeta(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class Page(BaseModel, Generic[ItemT]):
    items: list[ItemT]
    meta: PageMeta

    @classmethod
    def create(
        cls,
        *,
        items: list[ItemT],
        total: int,
        pagination: PaginationParams,
    ) -> Page[ItemT]:
        return cls(
            items=items,
            meta=PageMeta(
                page=pagination.page,
                limit=pagination.limit,
                total=total,
                total_pages=ceil(total / pagination.limit) if total else 0,
            ),
        )
