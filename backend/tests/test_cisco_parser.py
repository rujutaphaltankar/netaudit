import pytest

from app.parsers.cisco_ios import CiscoIosParser
from app.schemas.normalized import CredentialStorage, UnknownReason, ValueState, Vendor
from tests.conftest import read_sample

parser = CiscoIosParser()


@pytest.fixture(scope="module")
def weak():
    return parser.parse(read_sample("cisco_ios_weak.cfg"))


@pytest.fixture(scope="module")
def hardened():
    return parser.parse(read_sample("cisco_ios_hardened.cfg"))


def test_result_metadata(weak):
    assert weak.vendor == Vendor.CISCO_IOS and weak.parser_version == "0.1.0" and weak.schema_version == "1.0.0"


def test_weak_management_settings(weak):
    m = weak.config.management
    assert weak.config.hostname.value == "EDGE-SW-01"
    assert (m.ssh_enabled.value, m.ssh_version.value, m.telnet_enabled.value) == (True, "1", True)
    assert (m.http_enabled.value, m.https_enabled.value) == (True, False)
    assert m.admin_acls.state == ValueState.KNOWN and m.admin_acls.value == []
    assert m.session_timeout_minutes.value == 0.0


def test_weak_authentication_and_snmp(weak):
    a, s = weak.config.authentication, weak.config.snmp
    assert a.aaa_enabled.value is False and a.password_encryption_service.value is False
    assert a.privileged_credential_storage.value == CredentialStorage.REVERSIBLE
    assert set(a.local_user_credential_storage.value) == {CredentialStorage.MD5, CredentialStorage.REVERSIBLE}
    assert s.versions.value == ["v1/v2c"] and s.default_community_in_use.value is True


def test_missing_values_are_unknown_not_guessed(weak):
    assert weak.config.logging.remote_hosts.state == ValueState.UNKNOWN
    assert weak.config.authentication.methods.unknown_reason == UnknownReason.NOT_FOUND
    assert weak.config.ntp.authentication_enabled.state == ValueState.UNKNOWN


def test_hardened_settings(hardened):
    c = hardened.config
    assert c.management.ssh_version.value == "2" and c.management.telnet_enabled.value is False
    assert c.management.admin_acls.value == ["MGMT-ACL"] and c.management.session_timeout_minutes.value == 10
    assert c.authentication.methods.value == ["tacacs+", "local"]
    assert c.authentication.privileged_credential_storage.value == CredentialStorage.SCRYPT
    assert c.logging.remote_hosts.value == ["10.0.0.60"] and c.ntp.authentication_enabled.value is True
    assert c.snmp.versions.value == ["v3"] and c.snmp.v3_min_security_level.value == "authPriv"
    assert c.snmp.default_community_in_use.value is False
    assert c.detected_weak_settings == []


def test_weak_settings_detected_with_evidence(weak):
    ids = {w.identifier for w in weak.config.detected_weak_settings}
    assert {"telnet-enabled", "http-management-enabled", "ssh-v1-enabled", "snmp-default-community"} <= ids
    assert all(w.evidence for w in weak.config.detected_weak_settings)


def test_every_known_setting_has_evidence(weak, hardened):
    for result in (weak, hardened):
        for section in ("management", "authentication", "logging", "ntp", "snmp"):
            for name, setting in getattr(result.config, section):
                if setting.state == ValueState.KNOWN:
                    assert setting.evidence, f"{section}.{name} is KNOWN without evidence"


def test_banner_body_is_not_parsed_as_commands(weak):
    # The banner in the sample contains 'enable secret 0 ...' which must be ignored.
    assert weak.config.authentication.privileged_credential_storage.value == CredentialStorage.REVERSIBLE
    assert all("shouldNotBeParsed" not in u.text for u in weak.unknown_commands)


def test_unknown_commands_reported_with_line_numbers(weak, hardened):
    assert {u.text for u in weak.unknown_commands} == {"service tcp-keepalives-in", "ip ssh time-out 120"}
    assert all(u.line_number for u in hardened.unknown_commands)
    assert any(u.text.startswith("aaa authorization") for u in hardened.unknown_commands)


def test_secrets_never_appear_in_output(weak, hardened):
    blob = weak.model_dump_json() + hardened.model_dump_json()
    for secret in ("070C285F4D06", "0822455D0A16", "mERr$hx5rVt7", "FAKEhash", "FakeAuthPass123",
                   "FakePrivPass123", "FakeNtpKey123"):
        assert secret not in blob
    texts = [e.text for _, s in weak.config.snmp for e in s.evidence]
    assert any(t == "snmp-server community <redacted> RO" for t in texts)


def test_minimal_config_is_mostly_unknown():
    r = parser.parse("hostname R1\nline vty 0 4\n")
    m = r.config.management
    assert m.ssh_enabled.unknown_reason == UnknownReason.AMBIGUOUS
    assert m.telnet_enabled.unknown_reason == UnknownReason.AMBIGUOUS
    assert m.http_enabled.unknown_reason == UnknownReason.NOT_FOUND
    assert m.session_timeout_minutes.unknown_reason == UnknownReason.AMBIGUOUS
    assert r.config.snmp.versions.state == ValueState.UNKNOWN


def test_exec_timeout_minutes_and_seconds():
    r = parser.parse("hostname R1\nline vty 0 4\n exec-timeout 5 30\n transport input ssh\n")
    assert r.config.management.session_timeout_minutes.value == 5.5
    assert r.config.management.telnet_enabled.value is False


def test_no_http_overrides_earlier_http():
    r = parser.parse("hostname R1\nip http server\nno ip http server\n")
    assert r.config.management.http_enabled.value is False


def test_enable_secret_without_type_is_ambiguous():
    r = parser.parse("hostname R1\nenable secret mypassword\n")
    assert r.config.authentication.privileged_credential_storage.unknown_reason == UnknownReason.AMBIGUOUS


def test_empty_input_does_not_crash():
    r = parser.parse("")
    assert any(w.code == "no_statements" for w in r.warnings)
