from __future__ import annotations

from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded exclusively from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "Commercial Vehicle Parking Management API"
    version: str = "0.1.0"
    environment: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    docs_enabled: bool = True
    log_level: str = "INFO"

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "parking"

    jwt_secret_key: SecretStr = SecretStr("unsafe-development-secret-change-before-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=90)
    remember_me_refresh_token_expire_days: int = Field(default=30, ge=1, le=180)
    password_reset_token_expire_minutes: int = Field(default=30, ge=5, le=1440)

    backend_cors_origins: str = "http://localhost:3000,http://localhost:5173"
    allowed_hosts: str = "localhost,127.0.0.1"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def trusted_hosts(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @model_validator(mode="after")
    def validate_production_security(self) -> Self:
        secret = self.jwt_secret_key.get_secret_value()
        if self.is_production and (len(secret) < 32 or secret.startswith("unsafe-development")):
            raise ValueError(
                "JWT_SECRET_KEY must be a unique value of at least 32 characters in production."
            )
        if self.is_production and self.debug:
            raise ValueError("DEBUG must be disabled in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
