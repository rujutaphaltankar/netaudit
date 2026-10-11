"""Vendor-neutral normalized configuration schema.

Conventions (documented in docs/ARCHITECTURE.md):
  * Every extracted value is a *Setting*: either KNOWN (with a value and supporting
    evidence) or UNKNOWN (with a reason). Parsers never guess.
  * Absence of a global command is UNKNOWN/NOT_FOUND (configs may be partial and defaults
    vary by software version). Absence inside a block that is present and fully parsed,
    or inside a command family where other members were found, is treated as known.
  * Evidence text is always redacted before it is stored.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Self

from pydantic import BaseModel, Field, model_validator

SCHEMA_VERSION = "1.0.0"


class Vendor(str, Enum):
    CISCO_IOS = "cisco_ios"
    JUNIPER_JUNOS = "juniper_junos"
    PALO_ALTO_PANOS = "palo_alto_panos"
    FORTINET_FORTIOS = "fortinet_fortios"
    ARISTA_EOS = "arista_eos"


class ValueState(str, Enum):
    KNOWN = "known"
    UNKNOWN = "unknown"


class UnknownReason(str, Enum):
    NOT_FOUND = "not_found"        # nothing in the file addresses this setting
    AMBIGUOUS = "ambiguous"        # conflicting, partial or default-dependent evidence
    UNSUPPORTED = "unsupported"    # not modelled for this vendor
    UNRECOGNIZED = "unrecognized"  # present but not understood by the parser


class CredentialStorage:
    """Vendor-neutral names for how a credential is stored in the configuration."""

    CLEARTEXT = "cleartext"
    REVERSIBLE = "reversible"          # e.g. Cisco type 7, Junos $9$
    MD5 = "md5"                        # e.g. Cisco type 5, Junos $1$
    SHA256_UNSALTED = "sha256-unsalted"  # Cisco type 4
    SHA256 = "sha256"
    SHA512 = "sha512"
    PBKDF2_SHA256 = "pbkdf2-sha256"    # Cisco type 8
    SCRYPT = "scrypt"                  # Cisco type 9
    NONE = "none"                      # no password required


WEAK_CREDENTIAL_STORAGE = {
    CredentialStorage.CLEARTEXT,
    CredentialStorage.REVERSIBLE,
    CredentialStorage.MD5,
    CredentialStorage.SHA256_UNSALTED,
    CredentialStorage.NONE,
}


class Evidence(BaseModel):
    """A (redacted) source line supporting an extracted value."""

    line_number: int | None = None
    text: str
    context: str | None = None


class _Setting(BaseModel):
    state: ValueState = ValueState.UNKNOWN
    value: Any = None
    unknown_reason: UnknownReason | None = UnknownReason.NOT_FOUND
    evidence: list[Evidence] = Field(default_factory=list)
    note: str | None = None

    @model_validator(mode="after")
    def _check_state(self) -> Self:
        if self.state == ValueState.KNOWN:
            if self.value is None:
                raise ValueError("A KNOWN setting must have a value.")
            if self.unknown_reason is not None:
                raise ValueError("A KNOWN setting must not have an unknown_reason.")
        else:
            if self.value is not None:
                raise ValueError("An UNKNOWN setting must not carry a value.")
            if self.unknown_reason is None:
                raise ValueError("An UNKNOWN setting requires an unknown_reason.")
        return self

    @classmethod
    def known(cls, value: Any, evidence: list[Evidence] | None = None, note: str | None = None) -> Self:
        return cls(state=ValueState.KNOWN, value=value, unknown_reason=None,
                   evidence=list(evidence or []), note=note)

    @classmethod
    def unknown(cls, reason: UnknownReason = UnknownReason.NOT_FOUND,
                evidence: list[Evidence] | None = None, note: str | None = None) -> Self:
        return cls(state=ValueState.UNKNOWN, value=None, unknown_reason=reason,
                   evidence=list(evidence or []), note=note)


class BoolSetting(_Setting):
    value: bool | None = None


class StrSetting(_Setting):
    value: str | None = None


class FloatSetting(_Setting):
    value: float | None = None


class StrListSetting(_Setting):
    value: list[str] | None = None


class ManagementSettings(BaseModel):
    ssh_enabled: BoolSetting = Field(default_factory=BoolSetting.unknown)
    ssh_version: StrSetting = Field(default_factory=StrSetting.unknown)  # "2", "1" or "1,2"
    telnet_enabled: BoolSetting = Field(default_factory=BoolSetting.unknown)
    http_enabled: BoolSetting = Field(default_factory=BoolSetting.unknown)
    https_enabled: BoolSetting = Field(default_factory=BoolSetting.unknown)
    # ACL / filter names restricting management access (applied to every VTY block / lo0).
    admin_acls: StrListSetting = Field(default_factory=StrListSetting.unknown)
    # Worst-case interactive idle timeout in minutes; 0 means "never times out".
    session_timeout_minutes: FloatSetting = Field(default_factory=FloatSetting.unknown)


class AuthenticationSettings(BaseModel):
    aaa_enabled: BoolSetting = Field(default_factory=BoolSetting.unknown)
    # Ordered login methods: local, radius, tacacs+, group:<name>, enable, line, none.
    methods: StrListSetting = Field(default_factory=StrListSetting.unknown)
    password_encryption_service: BoolSetting = Field(default_factory=BoolSetting.unknown)
    privileged_credential_storage: StrSetting = Field(default_factory=StrSetting.unknown)
    local_user_credential_storage: StrListSetting = Field(default_factory=StrListSetting.unknown)


class LoggingSettings(BaseModel):
    remote_hosts: StrListSetting = Field(default_factory=StrListSetting.unknown)


class NtpSettings(BaseModel):
    servers: StrListSetting = Field(default_factory=StrListSetting.unknown)
    authentication_enabled: BoolSetting = Field(default_factory=BoolSetting.unknown)


class SnmpSettings(BaseModel):
    versions: StrListSetting = Field(default_factory=StrListSetting.unknown)  # "v1/v2c", "v3"
    v3_min_security_level: StrSetting = Field(default_factory=StrSetting.unknown)
    default_community_in_use: BoolSetting = Field(default_factory=BoolSetting.unknown)


class DetectedWeakness(BaseModel):
    """A weak setting that was positively detected. An empty list does NOT prove absence."""

    identifier: str
    category: str  # protocol | credential-storage | crypto | snmp
    description: str
    evidence: list[Evidence] = Field(default_factory=list)


class NormalizedConfig(BaseModel):
    schema_version: str = SCHEMA_VERSION
    vendor: Vendor
    hostname: StrSetting = Field(default_factory=StrSetting.unknown)
    management: ManagementSettings = Field(default_factory=ManagementSettings)
    authentication: AuthenticationSettings = Field(default_factory=AuthenticationSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    ntp: NtpSettings = Field(default_factory=NtpSettings)
    snmp: SnmpSettings = Field(default_factory=SnmpSettings)
    detected_weak_settings: list[DetectedWeakness] = Field(default_factory=list)
