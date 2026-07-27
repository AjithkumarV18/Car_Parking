from enum import StrEnum


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"
    PASSWORD_RESET = "password_reset"


class Role(StrEnum):
    """Platform roles. Add module-specific permissions without changing role middleware."""

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    OPERATOR = "operator"
    ATTENDANT = "attendant"
    VIEWER = "viewer"


class Permission(StrEnum):
    """Cross-cutting permission namespace; business permissions are added by future modules."""

    SYSTEM_READ = "system:read"
