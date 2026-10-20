"""Application settings, loaded from environment variables (or a local .env file).

Secrets (database URL, AI API key) live only in backend environment variables and
are never exposed to the frontend.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Network Security Compliance Auditor"
    app_version: str = "1.0.0"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    # Accepts postgres:// and postgresql:// URLs (Render style). When unset, a local SQLite file is used.
    database_url: str | None = None
    auto_migrate: bool = True  # run Alembic migrations on startup

    # Comma-separated list of allowed browser origins.
    cors_origins: str = "http://localhost:5100,http://localhost:5173"

    # Upload limits (configuration files are untrusted input).
    max_upload_bytes: int = 2 * 1024 * 1024
    max_lines: int = 100_000
    max_line_length: int = 8_192
    allowed_extensions: str = ".txt,.cfg,.conf,.config,.log,.set"

    # Optional AI assistance. The app must work without it (heuristic fallback).
    ai_api_key: str | None = None
    ai_model: str = "claude-sonnet-5-5"
    ai_timeout_seconds: float = 30.0
    ai_max_commands_per_request: int = 25

    # Authentication. In production JWT_SECRET and ADMIN_PASSWORD must be set explicitly.
    jwt_secret: str = "dev-insecure-secret-change-me-please-0123456789"
    jwt_expire_minutes: int = 60
    admin_username: str = "admin"
    admin_password: str | None = None
    seed_demo_data: bool = False
    samples_dir: str | None = None

    rate_limit_enabled: bool = True

    @field_validator("database_url")
    @classmethod
    def _normalise_database_url(cls, value: str | None) -> str | None:
        if not value:
            return None
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value[len("postgres://"):]
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value[len("postgresql://"):]
        return value

    @property
    def effective_database_url(self) -> str:
        return self.database_url or "sqlite:///./netaudit.db"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_extension_set(self) -> set[str]:
        return {e.strip().lower() for e in self.allowed_extensions.split(",") if e.strip()}

    @property
    def ai_enabled(self) -> bool:
        return bool(self.ai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
