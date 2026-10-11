import pytest

from app.parsers.juniper_junos import JuniperJunosParser
from app.schemas.normalized import CredentialStorage, UnknownReason, ValueState, Vendor
from tests.conftest import read_sample

parser = JuniperJunosParser()


@pytest.fixture(scope="module")
def weak():
    return parser.parse(read_sample("juniper_junos_weak.set"))


@pytest.fixture(scope="module")
def hardened():
    return parser.parse(read_sample("juniper_junos_hardened.conf"))


def test_weak_set_format(weak):
    c = weak.config
    assert weak.vendor == Vendor.JUNIPER_JUNOS and c.hostname.value == "EDGE-FW-01"
    m = c.management
    assert (m.ssh_enabled.value, m.ssh_version.value, m.telnet_enabled.value) == (True, "1", True)
    assert (m.http_enabled.value, m.https_enabled.value) == (True, False)
    assert c.authentication.privileged_credential_storage.value == CredentialStorage.MD5
    assert c.snmp.default_community_in_use.value is True
    assert c.ntp.authentication_enabled.value is False


def test_weak_unknown_states(weak):
    c = weak.config
    assert c.logging.remote_hosts.state == ValueState.UNKNOWN
    assert c.management.session_timeout_minutes.unknown_reason == UnknownReason.NOT_FOUND
    assert c.authentication.password_encryption_service.unknown_reason == UnknownReason.UNSUPPORTED


def test_hardened_hierarchical_format(hardened):
    c = hardened.config
    assert c.management.ssh_version.value == "2" and c.management.telnet_enabled.value is False
    assert c.management.https_enabled.value is True and c.management.admin_acls.value == ["PROTECT-RE"]
    assert c.management.session_timeout_minutes.value == 10
    assert c.authentication.methods.value == ["tacacs+", "local"]
    assert c.authentication.privileged_credential_storage.value == CredentialStorage.SHA512
    assert c.logging.remote_hosts.value == ["10.0.0.60"] and c.ntp.authentication_enabled.value is True
    assert c.snmp.versions.value == ["v3"] and c.snmp.v3_min_security_level.value == "authPriv"
    assert c.detected_weak_settings == []


def test_legacy_services_flagged(weak):
    assert "xnm-clear-text-enabled" in {w.identifier for w in weak.config.detected_weak_settings}


def test_evidence_has_original_line_numbers(hardened):
    ev = hardened.config.management.ssh_version.evidence[0]
    assert ev.line_number == 29 and ev.text == "set system services ssh protocol-version v2"


def test_set_and_hierarchical_formats_normalize_identically():
    hier = """system {
    host-name R1;
    services {
        ssh {
            protocol-version v2;
        }
    }
    ntp {
        server 10.0.0.1;
    }
}
"""
    flat = """set system host-name R1
set system services ssh protocol-version v2
set system ntp server 10.0.0.1
"""
    a, b = parser.parse(hier).config, parser.parse(flat).config
    for section in ("management", "authentication", "logging", "ntp", "snmp"):
        for (name, sa), (_, sb) in zip(getattr(a, section), getattr(b, section)):
            assert (sa.state, sa.value, sa.unknown_reason) == (sb.state, sb.value, sb.unknown_reason), name


def test_inactive_statements_are_ignored_and_reported():
    cfg = "system {\n    services {\n        ssh;\n        inactive: telnet;\n    }\n}\n"
    r = parser.parse(cfg)
    assert r.config.management.telnet_enabled.value is False
    assert any(w.code == "inactive_statements_ignored" for w in r.warnings)
    flat = parser.parse("set system services ssh\nset system services telnet\ndeactivate system services telnet\n")
    assert flat.config.management.telnet_enabled.value is False


def test_delete_removes_statement():
    r = parser.parse("set system services ssh\nset system services telnet\ndelete system services telnet\n")
    assert r.config.management.telnet_enabled.value is False


def test_services_absent_means_unknown_not_disabled():
    r = parser.parse("set system host-name R1\n")
    assert r.config.management.telnet_enabled.state == ValueState.UNKNOWN


def test_groups_produce_warning():
    r = parser.parse("set groups g1 system services telnet\nset apply-groups g1\nset system host-name R1\n")
    assert any(w.code == "groups_not_evaluated" for w in r.warnings)
    assert r.config.management.telnet_enabled.state == ValueState.UNKNOWN


def test_login_class_without_timeout_is_ambiguous():
    r = parser.parse("set system login class ops permissions all\nset system login class dev idle-timeout 5\n")
    assert r.config.management.session_timeout_minutes.unknown_reason == UnknownReason.AMBIGUOUS


def test_secrets_never_appear_in_output(weak, hardened):
    blob = weak.model_dump_json() + hardened.model_dump_json()
    for secret in ("FAKEFAKEFAKE", "FAKEHASH", "abcd1234", "zzzz9999"):
        assert secret not in blob
    texts = [e.text for _, s in weak.config.snmp for e in s.evidence]
    assert "set snmp community <redacted> authorization read-only" in texts


def test_unknown_commands(weak, hardened):
    assert [u.text for u in weak.unknown_commands] == ["set system services ssh root-login allow"]
    assert {u.text for u in hardened.unknown_commands} == {
        "set system services ssh root-login deny", "set system services ssh connection-limit 5"}


def test_malformed_input_does_not_crash():
    r = parser.parse("system {\n  services {\n    ssh;\n")
    assert any(w.code == "unbalanced_brace" for w in r.warnings)
    r = parser.parse("}\n}\n")
    assert r.warnings


def test_redaction_uses_original_tokens():
    from app.parsers.redaction import REDACTED, redact_junos_tokens
    tokens = ("system", "ntp", "authentication-key", "1", "type", "md5", "value", "$9$SECRETSECRET")
    assert redact_junos_tokens(tokens)[-1] == REDACTED and "$9$SECRETSECRET" not in redact_junos_tokens(tokens)
    assert redact_junos_tokens(("system", "ntp", "server", "10.0.0.1", "key", "1"))[-1] == "1"
