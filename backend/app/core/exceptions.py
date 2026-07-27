from __future__ import annotations

from typing import Any


class AppException(Exception):
    status_code = 500
    code = "internal_error"
    message = "An unexpected error occurred."

    def __init__(self, message: str | None = None, *, details: Any = None) -> None:
        self.message = message or self.message
        self.details = details
        super().__init__(self.message)


class AuthenticationError(AppException):
    status_code = 401
    code = "authentication_required"
    message = "Authentication is required."


class AuthorizationError(AppException):
    status_code = 403
    code = "access_denied"
    message = "You do not have permission to perform this action."


class NotFoundError(AppException):
    status_code = 404
    code = "not_found"
    message = "The requested resource was not found."


class ConflictError(AppException):
    status_code = 409
    code = "conflict"
    message = "The request conflicts with the current resource state."


class InvalidReceiptIdError(AppException):
    status_code = 422
    code = "invalid_receipt_id"
    message = "Receipt ID must be a valid 24-character identifier."


class DatabaseUnavailableError(AppException):
    status_code = 503
    code = "database_unavailable"
    message = "Database service is unavailable."


class InvalidBackupError(AppException):
    status_code = 422
    code = "invalid_backup"
    message = "The backup file is invalid or belongs to another company."
