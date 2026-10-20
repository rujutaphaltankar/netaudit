"""Rule-engine data models: rule definitions (loaded from catalog.json) and evaluation results."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.normalized import Evidence, UnknownReason


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Relative weight of each severity in the score.
SEVERITY_WEIGHT: dict[Severity, int] = {
    Severity.CRITICAL: 10, Severity.HIGH: 7, Severity.MEDIUM: 4, Severity.LOW: 2,
}
SEVERITY_ORDER = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]


class RuleStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"              # evidence missing/ambiguous: never counted as a pass
    NOT_APPLICABLE = "not_applicable"


class Condition(BaseModel):
    """A test on one normalized setting. `path` is dotted, e.g. `management.telnet_enabled`."""

    path: str
    op: str
    arg: Any = None
    message: str | None = None  # explanation used when this condition triggers N/A or FAIL


class Reference(BaseModel):
    framework: str
    control: str
    title: str


class Rule(BaseModel):
    id: str
    title: str
    category: str
    severity: Severity
    description: str                      # why this matters
    vendors: list[str] | None = None      # None = every supported vendor
    applies_when: list[Condition] = Field(default_factory=list)   # all must hold, else N/A
    fail_when: list[Condition] = Field(default_factory=list)      # any true -> FAIL
    check: Condition                      # true -> PASS, false -> FAIL, unknown -> UNKNOWN
    pass_message: str
    fail_message: str
    remediation: dict[str, str]           # keys: "generic" and/or vendor ids
    references: list[Reference] = Field(default_factory=list)


class RuleCatalog(BaseModel):
    catalog_version: str
    disclaimer: str
    rules: list[Rule]


class RuleResult(BaseModel):
    rule_id: str
    title: str
    category: str
    severity: Severity
    status: RuleStatus
    message: str
    observed: str | None = None
    unknown_reason: UnknownReason | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    remediation: str | None = None        # only populated for FAIL / UNKNOWN
    references: list[Reference] = Field(default_factory=list)


class AuditSummary(BaseModel):
    total_rules: int
    applicable: int
    evaluated: int                         # PASS + FAIL
    passed: int
    failed: int
    unknown: int
    not_applicable: int
    score: float | None                    # 0-100, None when nothing could be evaluated
    grade: str                             # A-F, or "N/A"
    coverage: float | None                 # evaluated / applicable (0-100)
    risk_level: str                        # critical | high | medium | low | none | undetermined
    failed_by_severity: dict[str, int]


class AuditEvaluation(BaseModel):
    catalog_version: str
    results: list[RuleResult]
    summary: AuditSummary
