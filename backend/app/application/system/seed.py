from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeedCredentials:
    admin_email: str
    admin_password: str
    super_admin_email: str
    super_admin_password: str


def validate_seed_credentials(credentials: SeedCredentials, *, is_production: bool) -> None:
    """Keep demo credentials deliberate and prevent unsafe production seeding."""

    for label, password in (("admin", credentials.admin_password), ("super admin", credentials.super_admin_password)):
        if len(password) < 12:
            raise ValueError(f"The {label} seed password must contain at least 12 characters.")
        strong_password = (
            any(char.islower() for char in password),
            any(char.isupper() for char in password),
            any(char.isdigit() for char in password),
            any(not char.isalnum() for char in password),
        )
        if not all(strong_password):
            raise ValueError(f"The {label} seed password must include upper, lower, number, and special characters.")
    if is_production:
        raise ValueError("Demo data seeding is disabled in production. Use an approved provisioning process instead.")
