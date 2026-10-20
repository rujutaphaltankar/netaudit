"""Deterministic compliance rule engine.

Guarantees:
  * PASS only when *known* evidence satisfies the check (missing/ambiguous evidence -> UNKNOWN).
  * No AI is involved in any verdict or score.
  * The score only counts evaluated rules (PASS/FAIL); `coverage` shows how much was evaluable.
"""
from __future__ import annotations

from typing import Any

from app.rules.loader import load_catalog
from app.rules.models import (
    SEVERITY_ORDER, SEVERITY_WEIGHT, AuditEvaluation, AuditSummary, Condition, Rule, RuleResult,
    RuleStatus, Severity,
)
from app.rules.operators import apply_operator
from app.schemas.normalized import Evidence, NormalizedConfig, UnknownReason, _Setting

VENDOR_LABEL = {"cisco_ios": "Cisco IOS", "juniper_junos": "Juniper Junos"}
REASON_TEXT = {
    UnknownReason.NOT_FOUND: "the configuration does not address this setting (it may be a partial config or rely on defaults)",
    UnknownReason.AMBIGUOUS: "the configuration contains conflicting or default-dependent evidence",
    UnknownReason.UNSUPPORTED: "this setting is not modelled for this vendor",
    UnknownReason.UNRECOGNIZED: "the relevant command was present but not understood by the parser",
}


def get_setting(cfg: NormalizedConfig, path: str) -> _Setting:
    obj: Any = cfg
    for part in path.split("."):
        obj = getattr(obj, part)
    return obj


def _test(cfg: NormalizedConfig, cond: Condition) -> bool | None:
    return apply_operator(cond.op, get_setting(cfg, cond.path), cond.arg)


def _dedupe(evidence: list[Evidence]) -> list[Evidence]:
    seen: set[tuple] = set()
    out = []
    for e in evidence:
        key = (e.line_number, e.text)
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


def _observed(setting: _Setting) -> str | None:
    if setting.value is None:
        return None
    v = setting.value
    return ", ".join(map(str, v)) if isinstance(v, list) and v else ("(none)" if v == [] else str(v))


def evaluate_rule(rule: Rule, cfg: NormalizedConfig) -> RuleResult:
    vendor = cfg.vendor.value
    base = dict(rule_id=rule.id, title=rule.title, category=rule.category, severity=rule.severity,
                references=rule.references)
    check_setting = get_setting(cfg, rule.check.path)
    related = [get_setting(cfg, c.path) for c in [*rule.applies_when, *rule.fail_when, rule.check]]
    evidence = _dedupe([e for s in related for e in s.evidence])
    remediation = rule.remediation.get(vendor) or rule.remediation.get("generic")

    def result(status: RuleStatus, message: str, **extra: Any) -> RuleResult:
        return RuleResult(**base, status=status, message=message, observed=_observed(check_setting),
                          evidence=evidence, **extra)

    if rule.vendors and vendor not in rule.vendors:
        return result(RuleStatus.NOT_APPLICABLE,
                      f"Not applicable to {VENDOR_LABEL.get(vendor, vendor)}.")
    for cond in rule.applies_when:
        t = _test(cfg, cond)
        if t is False:
            return result(RuleStatus.NOT_APPLICABLE, cond.message or "Precondition for this rule is not met.")
        if t is None:
            s = get_setting(cfg, cond.path)
            return result(RuleStatus.UNKNOWN,
                          "Applicability could not be determined: " + REASON_TEXT[s.unknown_reason],
                          unknown_reason=s.unknown_reason, remediation=remediation)
    for cond in rule.fail_when:
        if _test(cfg, cond) is True:
            return result(RuleStatus.FAIL, cond.message or rule.fail_message, remediation=remediation)

    outcome = _test(cfg, rule.check)
    if outcome is True:
        return result(RuleStatus.PASS, rule.pass_message)
    if outcome is False:
        return result(RuleStatus.FAIL, rule.fail_message, remediation=remediation)
    reason = check_setting.unknown_reason or UnknownReason.NOT_FOUND
    return result(RuleStatus.UNKNOWN,
                  "Could not be determined: " + REASON_TEXT[reason] + ". Treated as unverified, not as compliant.",
                  unknown_reason=reason, remediation=remediation)


def grade_for(score: float) -> str:
    return "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"


def summarize(results: list[RuleResult]) -> AuditSummary:
    by = lambda st: [r for r in results if r.status == st]  # noqa: E731
    passed, failed, unknown, na = by(RuleStatus.PASS), by(RuleStatus.FAIL), by(RuleStatus.UNKNOWN), by(RuleStatus.NOT_APPLICABLE)
    evaluated = len(passed) + len(failed)
    applicable = len(results) - len(na)
    total_w = sum(SEVERITY_WEIGHT[r.severity] for r in passed + failed)
    score = round(100 * sum(SEVERITY_WEIGHT[r.severity] for r in passed) / total_w, 1) if total_w else None
    failed_by_sev = {s.value: sum(1 for r in failed if r.severity == s) for s in SEVERITY_ORDER}

    if score is None:
        grade = "N/A"
    else:
        grade = grade_for(score)
        if failed_by_sev["critical"] and grade in ("A", "B", "C"):
            grade = "D"  # a critical failure caps the grade regardless of the weighted score
    risk = "undetermined" if score is None else next((s.value for s in SEVERITY_ORDER if failed_by_sev[s.value]), "none")
    return AuditSummary(
        total_rules=len(results), applicable=applicable, evaluated=evaluated, passed=len(passed),
        failed=len(failed), unknown=len(unknown), not_applicable=len(na), score=score, grade=grade,
        coverage=round(100 * evaluated / applicable, 1) if applicable else None,
        risk_level=risk, failed_by_severity=failed_by_sev,
    )


def evaluate_config(cfg: NormalizedConfig, rules: list[Rule] | None = None) -> AuditEvaluation:
    catalog = load_catalog()
    results = [evaluate_rule(r, cfg) for r in (rules if rules is not None else catalog.rules)]
    return AuditEvaluation(catalog_version=catalog.catalog_version, results=results, summary=summarize(results))
