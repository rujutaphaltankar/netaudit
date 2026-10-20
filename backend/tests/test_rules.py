import json

import pytest

from app.rules.engine import evaluate_config, summarize
from app.rules.loader import load_catalog, validate_catalog
from app.rules.models import RuleCatalog, RuleStatus
from app.rules.operators import apply_operator
from app.schemas.normalized import NormalizedConfig, ValueState, Vendor
from tests.helpers import parse_sample, results_by_id

C, J = Vendor.CISCO_IOS, Vendor.JUNIPER_JUNOS


def known(value):
    from app.schemas.normalized import BoolSetting
    return BoolSetting(state=ValueState.KNOWN, value=value, unknown_reason=None)


# ------------------------------------------------------------------------------------------ catalog
def test_catalog_is_valid_and_complete():
    cat = load_catalog()
    assert len(cat.rules) >= 15
    assert validate_catalog(cat) == []
    assert len({r.id for r in cat.rules}) == len(cat.rules)
    for r in cat.rules:
        assert r.references and "generic" in r.remediation and r.pass_message and r.fail_message


def test_catalog_validation_catches_mistakes():
    data = json.loads(json.dumps(load_catalog().model_dump(mode="json")))
    data["rules"][0]["check"]["path"] = "management.does_not_exist"
    data["rules"][1]["check"]["op"] = "bogus"
    data["rules"][2]["id"] = data["rules"][3]["id"]
    problems = " ".join(validate_catalog(RuleCatalog.model_validate(data)))
    assert "does_not_exist" in problems and "bogus" in problems and "duplicate rule id" in problems


# ------------------------------------------------------------------------------------- samples
def test_weak_cisco_scores_badly():
    ev = evaluate_config(parse_sample("cisco_ios_weak.cfg", C).config)
    r, s = results_by_id(ev), ev.summary
    assert s.score < 25 and s.grade == "F" and s.risk_level == "critical"
    assert r["NA-MGMT-001"].status == RuleStatus.FAIL           # telnet enabled
    assert r["NA-SNMP-002"].status == RuleStatus.FAIL           # default community
    assert r["NA-NTP-001"].status == RuleStatus.PASS
    assert r["NA-LOG-001"].status == RuleStatus.UNKNOWN         # no evidence -> never a pass
    assert r["NA-AUTH-003"].status == RuleStatus.NOT_APPLICABLE  # AAA disabled
    assert "AAA is disabled" in r["NA-AUTH-002"].message         # fail_when condition
    assert r["NA-MGMT-001"].evidence and r["NA-MGMT-001"].evidence[0].line_number
    assert "line vty" in r["NA-MGMT-001"].remediation           # vendor-specific remediation


def test_hardened_cisco_scores_well():
    ev = evaluate_config(parse_sample("cisco_ios_hardened.cfg", C).config)
    assert ev.summary.score >= 90 and ev.summary.grade == "A" and ev.summary.coverage == 100
    assert [x.rule_id for x in ev.results if x.status == RuleStatus.FAIL] == ["NA-NTP-002"]


def test_junos_samples_and_vendor_specific_rule():
    weak = results_by_id(evaluate_config(parse_sample("juniper_junos_weak.set", J).config))
    assert weak["NA-AUTH-004"].status == RuleStatus.NOT_APPLICABLE  # Cisco-only rule
    assert weak["NA-AUTH-001"].status == RuleStatus.UNKNOWN
    assert "delete system services telnet" in weak["NA-MGMT-001"].remediation
    hard = evaluate_config(parse_sample("juniper_junos_hardened.conf", J).config)
    assert hard.summary.grade == "A"


# -------------------------------------------------------------------------- core safety guarantees
def test_unknown_evidence_never_passes():
    ev = evaluate_config(NormalizedConfig(vendor=C))
    assert not [r for r in ev.results if r.status in (RuleStatus.PASS, RuleStatus.FAIL)]
    assert ev.summary.score is None and ev.summary.grade == "N/A" and ev.summary.risk_level == "undetermined"
    assert ev.summary.coverage == 0.0


def test_critical_failure_caps_grade():
    cfg = parse_sample("cisco_ios_hardened.cfg", C).config
    cfg.snmp.default_community_in_use = known(True)  # critical rule fails, everything else good
    s = evaluate_config(cfg).summary
    assert s.score > 80 and s.failed_by_severity["critical"] == 1 and s.grade == "D"


def test_summary_counts_add_up():
    s = evaluate_config(parse_sample("cisco_ios_weak.cfg", C).config).summary
    assert s.passed + s.failed + s.unknown + s.not_applicable == s.total_rules
    assert s.evaluated == s.passed + s.failed
    assert summarize([]).score is None


# ------------------------------------------------------------------------------------- operators
def test_operators_are_tristate():
    cfg = NormalizedConfig(vendor=C)
    assert apply_operator("is_true", cfg.management.telnet_enabled, None) is None
    assert apply_operator("is_false", known(False), None) is True
    assert apply_operator("is_false", known(True), None) is False


@pytest.mark.parametrize("value,expected", [(0, False), (10, True), (15, True), (16, False)])
def test_in_range(value, expected):
    from app.schemas.normalized import FloatSetting
    s = FloatSetting(state=ValueState.KNOWN, value=value, unknown_reason=None)
    assert apply_operator("in_range", s, {"gt": 0, "lte": 15}) is expected


def test_list_operators_and_wildcard():
    from app.schemas.normalized import StrListSetting
    s = StrListSetting(state=ValueState.KNOWN, value=["group:CORP", "local"], unknown_reason=None)
    assert apply_operator("includes_any", s, ["radius", "group:*"]) is True
    assert apply_operator("excludes_all", s, ["none"]) is True
    assert apply_operator("min_length", s, 3) is False
    assert apply_operator("non_empty", s, None) is True
