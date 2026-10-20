"""API models for audits, findings, users, AI mappings and dashboard statistics."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.rules.models import Reference, Severity
from app.schemas.api import ConfigParseResponse
from app.schemas.normalized import Evidence


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    username: str = Field(pattern=r"^[A-Za-z0-9_.-]{3,64}$")
    password: str = Field(min_length=8, max_length=128)
    role: Literal["admin", "viewer"] = "viewer"


class UserUpdate(BaseModel):
    is_active: bool | None = None
    role: Literal["admin", "viewer"] | None = None


class LoginRequest(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rule_id: str
    title: str
    category: str
    severity: str
    status: str
    message: str
    observed: str | None = None
    unknown_reason: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    remediation: str | None = None
    references: list[Reference] = Field(default_factory=list)


class AIMappingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    audit_id: int
    created_at: datetime
    vendor: str
    line_number: int | None = None
    command_text: str
    context: str | None = None
    meaning: str
    category: str
    security_impact: str
    confidence: str
    suggested_field: str | None = None
    note: str | None = None
    source: str
    status: str
    reviewed_at: datetime | None = None
    review_note: str | None = None
    audit_filename: str | None = None


class AuditItem(BaseModel):
    id: int
    created_at: datetime
    created_by: str | None = None
    filename: str
    sha256: str
    vendor: str
    hostname: str | None = None
    score: float | None = None
    grade: str
    risk_level: str
    coverage: float | None = None
    passed: int
    failed: int
    unknown: int
    not_applicable: int
    failed_by_severity: dict[str, int] = Field(default_factory=dict)


class AuditDetail(AuditItem):
    catalog_version: str
    parser_version: str
    line_count: int
    size_bytes: int
    findings: list[FindingOut]
    parse: ConfigParseResponse
    ai_mappings: list[AIMappingOut] = Field(default_factory=list)


class AuditPage(BaseModel):
    items: list[AuditItem]
    total: int
    page: int
    page_size: int


class ReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str | None = Field(default=None, max_length=500)


class RuleOut(BaseModel):
    id: str
    title: str
    category: str
    severity: Severity
    description: str
    vendors: list[str] | None = None
    remediation: dict[str, str]
    references: list[Reference]


class RuleCatalogOut(BaseModel):
    catalog_version: str
    disclaimer: str
    rules: list[RuleOut]


class TrendPoint(BaseModel):
    id: int
    created_at: datetime
    filename: str
    score: float | None


class TopRule(BaseModel):
    rule_id: str
    title: str
    severity: str
    count: int


class DashboardStats(BaseModel):
    total_audits: int
    average_score: float | None
    pending_ai_reviews: int
    by_vendor: dict[str, int]
    by_grade: dict[str, int]
    failed_by_severity: dict[str, int]
    score_trend: list[TrendPoint]
    top_failing_rules: list[TopRule]
    recent: list[AuditItem]


class FindingChange(BaseModel):
    rule_id: str
    title: str
    severity: str
    base_status: str | None
    target_status: str | None
    change: Literal["improved", "regressed", "unchanged"]


class AuditComparison(BaseModel):
    base: AuditItem
    target: AuditItem
    score_delta: float | None
    changes: list[FindingChange]
