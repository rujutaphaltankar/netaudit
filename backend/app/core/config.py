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
    app_version: str = "0.1.0"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    # Optional until Phase 6. Accepts postgres:// and postgresql:// URLs (Render style).
    database_url: str | None = None

    # Comma-separated list of allowed browser origins.
    cors_origins: str = "http://localhost:5173"

    # Upload limits (configuration files are untrusted input).
    max_upload_bytes: int = 2 * 1024 * 1024
    max_lines: int = 100_000
    max_line_length: int = 8_192
    allowed_extensions: str = ".txt,.cfg,.conf,.config,.log,.set"

    # Optional AI assistance (Phase 5). The app must work without it.
    ai_api_key: str | None = None

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
