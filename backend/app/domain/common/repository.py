from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

EntityType = TypeVar("EntityType")


class Repository(ABC, Generic[EntityType]):
    """Persistence port implemented by infrastructure adapters."""

    @abstractmethod
    async def get_by_id(self, entity_id: str) -> EntityType | None: ...

    @abstractmethod
    async def create(self, entity: EntityType) -> EntityType: ...

    @abstractmethod
    async def update(self, entity: EntityType) -> EntityType: ...

    @abstractmethod
    async def delete(self, entity_id: str) -> None: ...
