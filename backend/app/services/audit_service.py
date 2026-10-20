"""Persistence and querying of audits."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import AIMapping, Audit, Finding, User
from app.rules.models import AuditEvaluation, RuleStatus
from app.schemas.api import ConfigParseResponse
from app.schemas.audit import (
    AIMappingOut, AuditComparison, AuditDetail, AuditItem, DashboardStats, FindingChange, FindingOut,
    TopRule, TrendPoint,
)

SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
STATUS_ORDER = {"fail": 0, "unknown": 1, "pass": 2, "not_applicable": 3}
STATUS_RANK = {"fail": 0, "unknown": 1, "not_applicable": 2, "pass": 3}  # higher = better


def persist_audit(db: Session, user: User | None, parsed: ConfigParseResponse, evaluation: AuditEvaluation,
                  created_at: datetime | None = None) -> Audit:
    s = evaluation.summary
    audit = Audit(
        created_by_id=user.id if user else None, filename=parsed.file.filename, sha256=parsed.file.sha256,
        size_bytes=parsed.file.size_bytes, line_count=parsed.file.line_count, vendor=parsed.vendor_used.value,
        hostname=parsed.result.config.hostname.value, parser_version=parsed.result.parser_version,
        catalog_version=evaluation.catalog_version, score=s.score, grade=s.grade, risk_level=s.risk_level,
        coverage=s.coverage, passed=s.passed, failed=s.failed, unknown=s.unknown, not_applicable=s.not_applicable,
        summary=s.model_dump(mode="json"), parse_response=parsed.model_dump(mode="json"),
    )
    if created_at:
        audit.created_at = created_at
    audit.findings = [
        Finding(rule_id=r.rule_id, title=r.title, category=r.category, severity=r.severity.value,
                status=r.status.value, message=r.message, observed=r.observed,
                unknown_reason=r.unknown_reason.value if r.unknown_reason else None,
                evidence=[e.model_dump(mode="json") for e in r.evidence], remediation=r.remediation,
                references=[x.model_dump(mode="json") for x in r.references])
        for r in evaluation.results
    ]
    db.add(audit)
    db.commit()
    return audit


def get_audit_or_404(db: Session, audit_id: int) -> Audit:
    audit = db.get(Audit, audit_id)
    if audit is None:
        raise AppError(404, "audit_not_found", f"Audit {audit_id} was not found.")
    return audit


def to_item(a: Audit) -> AuditItem:
    return AuditItem(
        id=a.id, created_at=a.created_at, created_by=a.created_by.username if a.created_by else None,
        filename=a.filename, sha256=a.sha256, vendor=a.vendor, hostname=a.hostname, score=a.score, grade=a.grade,
        risk_level=a.risk_level, coverage=a.coverage, passed=a.passed, failed=a.failed, unknown=a.unknown,
        not_applicable=a.not_applicable, failed_by_severity=a.summary.get("failed_by_severity", {}),
    )


def sorted_findings(a: Audit) -> list[Finding]:
    return sorted(a.findings, key=lambda f: (STATUS_ORDER[f.status], SEV_ORDER[f.severity], f.rule_id))


def mapping_out(m: AIMapping) -> AIMappingOut:
    out = AIMappingOut.model_validate(m)
    out.audit_filename = m.audit.filename if m.audit else None
    return out


def to_detail(a: Audit) -> AuditDetail:
    return AuditDetail(
        **to_item(a).model_dump(), catalog_version=a.catalog_version, parser_version=a.parser_version,
        line_count=a.line_count, size_bytes=a.size_bytes,
        findings=[FindingOut.model_validate(f) for f in sorted_findings(a)],
        parse=ConfigParseResponse.model_validate(a.parse_response),
        ai_mappings=[mapping_out(m) for m in a.ai_mappings],
    )


def list_audits(db: Session, page: int, page_size: int, vendor: str | None, q: str | None) -> tuple[list[Audit], int]:
    stmt = select(Audit)
    if vendor:
        stmt = stmt.where(Audit.vendor == vendor)
    if q:
        like = f"%{q.strip()[:80]}%"
        stmt = stmt.where(or_(Audit.filename.ilike(like), Audit.hostname.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Audit.created_at.desc(), Audit.id.desc())
                      .offset((page - 1) * page_size).limit(page_size)).all()
    return list(rows), total


def dashboard_stats(db: Session) -> DashboardStats:
    audits = db.scalars(select(Audit).order_by(Audit.created_at.asc(), Audit.id.asc())).all()
    scored = [a.score for a in audits if a.score is not None]
    sev_totals = {s: 0 for s in SEV_ORDER}
    by_vendor: dict[str, int] = {}
    by_grade: dict[str, int] = {}
    for a in audits:
        by_vendor[a.vendor] = by_vendor.get(a.vendor, 0) + 1
        by_grade[a.grade] = by_grade.get(a.grade, 0) + 1
        for k, v in a.summary.get("failed_by_severity", {}).items():
            sev_totals[k] = sev_totals.get(k, 0) + v
    top = db.execute(
        select(Finding.rule_id, Finding.title, Finding.severity, func.count().label("n"))
        .where(Finding.status == RuleStatus.FAIL.value).group_by(Finding.rule_id, Finding.title, Finding.severity)
        .order_by(func.count().desc(), Finding.rule_id).limit(8)).all()
    pending = db.scalar(select(func.count()).select_from(AIMapping).where(AIMapping.status == "pending")) or 0
    return DashboardStats(
        total_audits=len(audits), average_score=round(sum(scored) / len(scored), 1) if scored else None,
        pending_ai_reviews=pending, by_vendor=by_vendor, by_grade=by_grade, failed_by_severity=sev_totals,
        score_trend=[TrendPoint(id=a.id, created_at=a.created_at, filename=a.filename, score=a.score) for a in audits[-20:]],
        top_failing_rules=[TopRule(rule_id=r.rule_id, title=r.title, severity=r.severity, count=r.n) for r in top],
        recent=[to_item(a) for a in reversed(audits[-5:])],
    )


def compare_audits(base: Audit, target: Audit) -> AuditComparison:
    b = {f.rule_id: f for f in base.findings}
    t = {f.rule_id: f for f in target.findings}
    changes = []
    for rule_id in sorted(set(b) | set(t)):
        fb, ft = b.get(rule_id), t.get(rule_id)
        rb = STATUS_RANK.get(fb.status, -1) if fb else -1
        rt = STATUS_RANK.get(ft.status, -1) if ft else -1
        ref = ft or fb
        changes.append(FindingChange(
            rule_id=rule_id, title=ref.title, severity=ref.severity, base_status=fb.status if fb else None,
            target_status=ft.status if ft else None,
            change="improved" if rt > rb else "regressed" if rt < rb else "unchanged"))
    changes.sort(key=lambda c: (c.change == "unchanged", SEV_ORDER[c.severity], c.rule_id))
    delta = round(target.score - base.score, 1) if base.score is not None and target.score is not None else None
    return AuditComparison(base=to_item(base), target=to_item(target), score_delta=delta, changes=changes)
