from __future__ import annotations

import logging
from contextvars import ContextVar
from logging.config import dictConfig

from pythonjsonlogger.json import JsonFormatter

from app.core.config import Settings

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestContextFilter(logging.Filter):
    """Ensures structured fields are present even outside a request context."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_context.get()
        return True


def configure_logging(settings: Settings) -> None:
    """Configure JSON logs for container-friendly aggregation."""

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"request_context": {"()": RequestContextFilter}},
            "formatters": {
                "json": {
                    "()": JsonFormatter,
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "filters": ["request_context"],
                }
            },
            "root": {"handlers": ["console"], "level": settings.log_level.upper()},
        }
    )
