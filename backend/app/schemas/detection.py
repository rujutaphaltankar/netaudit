from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.normalized import Vendor


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class VendorDetection(BaseModel):
    detected_vendor: Vendor | None = None
    confidence: Confidence = Confidence.NONE
    supported: bool = False
    signals: list[str] = Field(default_factory=list)
    scores: dict[str, int] = Field(default_factory=dict)
