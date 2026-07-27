from __future__ import annotations

import logging
from datetime import UTC

from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import Settings
from app.core.exceptions import DatabaseUnavailableError

logger = logging.getLogger(__name__)


class MongoConnection:
    """Owns the Mongo client for the application's lifespan."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.client: AsyncIOMotorClient | None = None

    async def connect(self) -> None:
        self.client = AsyncIOMotorClient(
            self._settings.mongodb_uri,
            uuidRepresentation="standard",
            tz_aware=True,
            tzinfo=UTC,
        )
        await self.client.admin.command("ping")
        logger.info("MongoDB connection established")

    async def close(self) -> None:
        if self.client:
            self.client.close()
            self.client = None
            logger.info("MongoDB connection closed")

    @property
    def database(self) -> AsyncIOMotorDatabase:
        if self.client is None:
            raise DatabaseUnavailableError()
        return self.client[self._settings.mongodb_database]


def get_database(request: Request) -> AsyncIOMotorDatabase:
    """FastAPI dependency for future Mongo repository providers."""

    connection: MongoConnection | None = getattr(request.app.state, "mongo", None)
    if connection is None:
        raise DatabaseUnavailableError()
    return connection.database
