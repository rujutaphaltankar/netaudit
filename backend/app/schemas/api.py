"""API request/response models."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.detection import VendorDetection
from app.schemas.normalized import Vendor
from app.schemas.parsing import ParseResult, ParseWarning


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    app: str
    version: str
    environment: str
    database: Literal["not_configured", "ok", "unavailable"]
    ai_assistance: Literal["enabled", "fallback_only"]
    time: datetime


class VendorInfo(BaseModel):
    id: Vendor
    display_name: str
    supported: bool
    parser_version: str | None = None


class FileInfo(BaseModel):
    filename: str
    size_bytes: int
    sha256: str
    line_count: int
    encoding: str


class ConfigParseResponse(BaseModel):
    file: FileInfo
    requested_vendor: str
    vendor_used: Vendor
    detection: VendorDetection
    result: ParseResult
    warnings: list[ParseWarning] = Field(default_factory=list)


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorBody
