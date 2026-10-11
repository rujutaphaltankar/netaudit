"""Derive detected weak settings from an already-normalized configuration (vendor neutral)."""
from __future__ import annotations

from app.schemas.normalized import DetectedWeakness, NormalizedConfig, WEAK_CREDENTIAL_STORAGE


def derive_weak_settings(cfg: NormalizedConfig) -> list[DetectedWeakness]:
    out: list[DetectedWeakness] = []
    m, a, s = cfg.management, cfg.authentication, cfg.snmp

    if m.telnet_enabled.value is True:
        out.append(DetectedWeakness(
            identifier="telnet-enabled", category="protocol",
            description="Telnet is enabled; it sends credentials and session data in clear text.",
            evidence=m.telnet_enabled.evidence))
    if m.http_enabled.value is True:
        out.append(DetectedWeakness(
            identifier="http-management-enabled", category="protocol",
            description="Unencrypted HTTP management access is enabled.",
            evidence=m.http_enabled.evidence))
    if m.ssh_version.value in ("1", "1,2"):
        out.append(DetectedWeakness(
            identifier="ssh-v1-enabled", category="crypto",
            description="SSH protocol version 1 is permitted; it has known cryptographic weaknesses.",
            evidence=m.ssh_version.evidence))
    if a.privileged_credential_storage.value in WEAK_CREDENTIAL_STORAGE:
        out.append(DetectedWeakness(
            identifier="weak-privileged-credential-storage", category="credential-storage",
            description=f"The privileged credential is stored as '{a.privileged_credential_storage.value}', "
                        "which is considered weak.",
            evidence=a.privileged_credential_storage.evidence))
    weak_users = sorted(set(a.local_user_credential_storage.value or []) & WEAK_CREDENTIAL_STORAGE)
    if weak_users:
        out.append(DetectedWeakness(
            identifier="weak-local-user-credential-storage", category="credential-storage",
            description="Local user credentials use weak storage: " + ", ".join(weak_users) + ".",
            evidence=a.local_user_credential_storage.evidence))
    if "v1/v2c" in (s.versions.value or []):
        out.append(DetectedWeakness(
            identifier="snmp-community-strings-in-use", category="snmp",
            description="SNMPv1/v2c community strings are configured; they are sent in clear text.",
            evidence=s.versions.evidence))
    if s.default_community_in_use.value is True:
        out.append(DetectedWeakness(
            identifier="snmp-default-community", category="snmp",
            description="A well-known default SNMP community string (public/private) is configured.",
            evidence=s.default_community_in_use.evidence))
    if s.v3_min_security_level.value == "noAuthNoPriv":
        out.append(DetectedWeakness(
            identifier="snmp-v3-no-auth-no-priv", category="snmp",
            description="SNMPv3 is configured without authentication or privacy.",
            evidence=s.v3_min_security_level.evidence))
    return out
