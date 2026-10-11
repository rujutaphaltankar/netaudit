"""Parser output models."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.normalized import NormalizedConfig, Vendor


class ParseWarning(BaseModel):
    code: str
    message: str
    line_number: int | None = None


class UnknownCommand(BaseModel):
    """A security-relevant command the parser did not understand (input to Phase 5)."""

    vendor: Vendor
    line_number: int | None = None
    text: str  # redacted
    context: str | None = None


class ParseResult(BaseModel):
    parser_name: str
    parser_version: str
    schema_version: str
    vendor: Vendor
    config: NormalizedConfig
    warnings: list[ParseWarning] = Field(default_factory=list)
    unknown_commands: list[UnknownCommand] = Field(default_factory=list)
    line_count: int = 0
