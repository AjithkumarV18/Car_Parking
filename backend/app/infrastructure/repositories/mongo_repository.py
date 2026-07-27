from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.domain.common.repository import Repository
from app.shared.pagination import Page, PaginationParams

EntityType = TypeVar("EntityType")


class MongoRepository(Repository[EntityType], ABC, Generic[EntityType]):
    """Reusable Mongo base adapter; context repositories provide mapping details."""

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self.collection = collection

    @abstractmethod
    def to_entity(self, document: dict[str, Any]) -> EntityType: ...

    @abstractmethod
    def to_document(self, entity: EntityType) -> dict[str, Any]: ...

    async def get_by_id(self, entity_id: str) -> EntityType | None:
        if not ObjectId.is_valid(entity_id):
            return None
        document = await self.collection.find_one({"_id": ObjectId(entity_id)})
        return self.to_entity(document) if document else None

    async def create(self, entity: EntityType) -> EntityType:
        document = self.to_document(entity)
        result = await self.collection.insert_one(document)
        created = await self.collection.find_one({"_id": result.inserted_id})
        if created is None:  # Defensive: Mongo acknowledged an insert but cannot read it.
            raise RuntimeError("Created document could not be retrieved.")
        return self.to_entity(created)

    async def update(self, entity: EntityType) -> EntityType:
        document = self.to_document(entity)
        raw_id = document.pop("_id", document.pop("id", None))
        if not raw_id or not ObjectId.is_valid(str(raw_id)):
            raise ValueError("A valid entity id is required for update.")
        object_id = ObjectId(str(raw_id))
        await self.collection.update_one({"_id": object_id}, {"$set": document})
        updated = await self.collection.find_one({"_id": object_id})
        if updated is None:
            raise RuntimeError("Updated document could not be retrieved.")
        return self.to_entity(updated)

    async def delete(self, entity_id: str) -> None:
        if not ObjectId.is_valid(entity_id):
            return
        await self.collection.delete_one({"_id": ObjectId(entity_id)})

    async def page(
        self,
        pagination: PaginationParams,
        query: dict[str, Any] | None = None,
    ) -> Page[EntityType]:
        filter_query = query or {}
        total = await self.collection.count_documents(filter_query)
        cursor = self.collection.find(filter_query).skip(pagination.offset).limit(pagination.limit)
        items = [self.to_entity(document) async for document in cursor]
        return Page.create(items=items, total=total, pagination=pagination)
