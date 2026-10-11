"""Juniper Junos-style configuration parser (parser version 0.1.0).

Supports both `set` format and hierarchical (curly-brace) format. Both are flattened into
statements with a full token path, so extraction logic is identical for the two formats.
Evidence is shown as the normalized `set ...` statement with the original line number.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.parsers.base import BaseConfigParser
from app.parsers.redaction import redact_junos_tokens
from app.parsers.weakness import derive_weak_settings
from app.schemas.normalized import (
    SCHEMA_VERSION, AuthenticationSettings, BoolSetting, CredentialStorage, DetectedWeakness,
    Evidence, FloatSetting, LoggingSettings, ManagementSettings, NormalizedConfig, NtpSettings,
    SnmpSettings, StrListSetting, StrSetting, UnknownReason, Vendor,
)
from app.schemas.parsing import ParseResult, ParseWarning, UnknownCommand

Path = tuple[str, ...]
_TOKEN_RE = re.compile(r'"([^"]*)"|(\S+)')


@dataclass
class Stmt:
    number: int
    path: Path
    leaf: bool = True
    inactive: bool = False


def _tokens(text: str) -> list[str]:
    out = [m.group(1) if m.group(1) is not None else m.group(2) for m in _TOKEN_RE.finditer(text)]
    return [t for t in out if t not in ("[", "]")]


def _strip_comments(line: str) -> str:
    line = re.sub(r"/\*.*?\*/", "", line)
    return re.sub(r"(^|\s)##.*$", "", line).strip()


def _matches(path: Path, pattern: Path) -> bool:
    return len(path) >= len(pattern) and all(p == "*" or p == t for p, t in zip(pattern, path))


def _is_set_format(content: str) -> bool:
    set_lines = brace_lines = 0
    for raw in content.split("\n"):
        s = raw.strip()
        if re.match(r"^(set|deactivate|delete)\s+\S", s):
            set_lines += 1
        elif s.endswith("{"):
            brace_lines += 1
    return set_lines > 0 and set_lines >= brace_lines


def parse_statements(content: str) -> tuple[list[Stmt], list[ParseWarning]]:
    warnings: list[ParseWarning] = []
    stmts: list[Stmt] = []
    if _is_set_format(content):
        for number, raw in enumerate(content.split("\n"), start=1):
            line = _strip_comments(raw.strip())
            if not line or line.startswith("#"):
                continue
            toks = _tokens(line)
            verb, path = toks[0], tuple(toks[1:])
            if verb == "set" and path:
                stmts.append(Stmt(number, path))
            elif verb == "deactivate" and path:
                for s in stmts:
                    if _matches(s.path, path):
                        s.inactive = True
            elif verb == "delete" and path:
                stmts = [s for s in stmts if not _matches(s.path, path)]
            else:
                warnings.append(ParseWarning(code="unparsed_line", line_number=number,
                                             message="Line is not a recognized set/deactivate/delete statement."))
        return stmts, warnings

    stack: list[tuple[list[str], bool]] = []
    in_comment = False
    for number, raw in enumerate(content.split("\n"), start=1):
        line = raw.strip()
        if in_comment:
            in_comment = "*/" not in line
            continue
        if line.startswith("/*") and "*/" not in line:
            in_comment = True
            continue
        line = _strip_comments(line)
        if not line or line.startswith("#"):
            continue
        base = tuple(t for toks, _ in stack for t in toks)
        stack_inactive = any(inact for _, inact in stack)
        if line.endswith("{"):
            toks = _tokens(line[:-1])
            inactive = bool(toks) and toks[0] == "inactive:"
            toks = [t for t in toks if t != "inactive:"]
            stack.append((toks, inactive))
            if toks:
                stmts.append(Stmt(number, base + tuple(toks), leaf=False, inactive=stack_inactive or inactive))
        elif line == "}":
            if stack:
                stack.pop()
            else:
                warnings.append(ParseWarning(code="unbalanced_brace", line_number=number,
                                             message="Closing brace without a matching opening brace."))
        elif line.endswith(";"):
            toks = _tokens(line[:-1])
            inactive = bool(toks) and toks[0] == "inactive:"
            toks = [t for t in toks if t != "inactive:"]
            if toks:
                stmts.append(Stmt(number, base + tuple(toks), inactive=stack_inactive or inactive))
        else:
            warnings.append(ParseWarning(code="unparsed_line", line_number=number,
                                         message="Line is not a recognized Junos statement or block."))
    if stack:
        warnings.append(ParseWarning(code="unbalanced_brace", message="One or more blocks were not closed."))
    return stmts, warnings


# --------------------------------------------------------------------------- extraction

_HASH_STORAGE = (("$9$", CredentialStorage.REVERSIBLE), ("$1$", CredentialStorage.MD5),
                 ("$5$", CredentialStorage.SHA256), ("$6$", CredentialStorage.SHA512))
_AUTH_ORDER_MAP = {"password": "local", "radius": "radius", "tacplus": "tacacs+"}
_LEGACY_SERVICES = {"ftp": "FTP", "rlogin": "rlogin", "rsh": "rsh", "finger": "finger",
                    "xnm-clear-text": "clear-text XML API (xnm-clear-text)"}
_SNMP_AUTH = {"authentication-md5", "authentication-sha", "authentication-sha224",
              "authentication-sha256", "authentication-sha384", "authentication-sha512"}
_SNMP_PRIV = {"privacy-aes128", "privacy-des", "privacy-3des"}
_LEVEL_RANK = {"noAuthNoPriv": 0, "authNoPriv": 1, "authPriv": 2}

_RELEVANT_ROOTS: list[Path] = [
    ("system", "services"), ("system", "login"), ("system", "authentication-order"),
    ("system", "radius-server"), ("system", "tacplus-server"), ("system", "syslog"),
    ("system", "ntp"), ("system", "root-authentication"), ("snmp",),
]
_BENIGN: list[Path] = [
    ("system", "login", "user", "*", "uid"), ("system", "login", "user", "*", "class"),
    ("system", "login", "user", "*", "full-name"), ("system", "login", "message"),
    ("system", "login", "class", "*", "permissions"), ("system", "login", "class", "*", "allow-commands"),
    ("system", "login", "class", "*", "deny-commands"),
    ("system", "syslog", "file"), ("system", "syslog", "user"), ("system", "syslog", "console"),
    ("system", "ntp", "boot-server"),
    ("system", "services", "web-management", "https", "system-generated-certificate"),
    ("system", "services", "web-management", "https", "pki-local-certificate"),
    ("snmp", "location"), ("snmp", "contact"), ("snmp", "description"), ("snmp", "trap-group"),
    ("snmp", "trap-options"), ("snmp", "view"),
]


def classify_junos_hash(value: str) -> str | None:
    for prefix, storage in _HASH_STORAGE:
        if value.startswith(prefix):
            return storage
    return None


class _Extractor:
    def __init__(self, stmts: list[Stmt]) -> None:
        self.stmts = [s for s in stmts if not s.inactive and s.path[0] != "groups"]
        self.consumed: set[int] = set()
        self.warnings: list[ParseWarning] = []

    def find(self, *pattern: str) -> list[Stmt]:
        return [s for s in self.stmts if _matches(s.path, pattern)]

    def ev(self, s: Stmt) -> Evidence:
        self.consumed.add(id(s))
        return Evidence(line_number=s.number, text="set " + " ".join(redact_junos_tokens(s.path)))

    def claim(self, *pattern: str) -> None:
        for s in self.find(*pattern):
            self.consumed.add(id(s))

    def shortest(self, found: list[Stmt]) -> Evidence:
        return self.ev(min(found, key=lambda s: (len(s.path), s.number)))

    def services_flag(self, *path: str) -> BoolSetting:
        found = self.find("system", "services", *path)
        if found:
            return BoolSetting.known(True, [self.shortest(found)])
        services = self.find("system", "services")
        if services:
            return BoolSetting.known(False, [self.shortest(services)],
                                     f"'{' '.join(path)}' is not enabled under 'system services' (services are opt-in).")
        return BoolSetting.unknown(UnknownReason.NOT_FOUND, note="No 'system services' configuration found.")

    # -- management
    def management(self) -> ManagementSettings:
        for s in self.stmts:
            if _matches(s.path, ("system", "services", "*")) and len(s.path) == 3:
                self.consumed.add(id(s))
        return ManagementSettings(
            ssh_enabled=self.services_flag("ssh"),
            ssh_version=self.ssh_version(),
            telnet_enabled=self.services_flag("telnet"),
            http_enabled=self.services_flag("web-management", "http"),
            https_enabled=self.services_flag("web-management", "https"),
            admin_acls=self.admin_acls(),
            session_timeout_minutes=self.timeout(),
        )

    def ssh_version(self) -> StrSetting:
        found = self.find("system", "services", "ssh", "protocol-version")
        versions = {t for s in found for t in s.path[4:] if t in ("v1", "v2")}
        if not versions:
            return StrSetting.unknown(UnknownReason.NOT_FOUND,
                                      note="'ssh protocol-version' not set; the default depends on the Junos release.")
        value = "1,2" if versions == {"v1", "v2"} else "1" if versions == {"v1"} else "2"
        return StrSetting.known(value, [self.ev(s) for s in found])

    def admin_acls(self) -> StrListSetting:
        lo0 = self.find("interfaces", "lo0")
        if not lo0:
            return StrListSetting.unknown(UnknownReason.NOT_FOUND, note="No lo0 interface configuration found.")
        applied = [s for s in self.find("interfaces", "lo0", "unit", "*", "family", "*", "filter", "input")
                   + self.find("interfaces", "lo0", "unit", "*", "family", "*", "filter", "input-list")
                   if len(s.path) > 8]
        names = list(dict.fromkeys(t for s in applied for t in s.path[8:]))
        evidence = [self.ev(s) for s in applied] or [self.shortest(lo0)]
        return StrListSetting.known(names, evidence,
                                    "Filter attachment on lo0 detected; filter contents are not evaluated.")

    def timeout(self) -> FloatSetting:
        classes = {s.path[3] for s in self.find("system", "login", "class", "*")}
        if not classes:
            return FloatSetting.unknown(UnknownReason.NOT_FOUND, note="No user-defined login class found.")
        values: dict[str, float] = {}
        evidence: list[Evidence] = []
        for s in self.find("system", "login", "class", "*", "idle-timeout", "*"):
            try:
                values[s.path[3]] = float(s.path[5])
                evidence.append(self.ev(s))
            except ValueError:
                self.warnings.append(ParseWarning(code="invalid_idle_timeout", line_number=s.number,
                                                  message="idle-timeout is not numeric."))
        if classes - values.keys():
            return FloatSetting.unknown(
                UnknownReason.AMBIGUOUS, evidence,
                "Not every defined login class sets idle-timeout: " + ", ".join(sorted(classes - values.keys())) + ".")
        return FloatSetting.known(max(values.values()), evidence, "Worst case across user-defined login classes.")

    # -- authentication
    def authentication(self) -> AuthenticationSettings:
        order = self.find("system", "authentication-order")
        servers = self.find("system", "radius-server") + self.find("system", "tacplus-server")
        for s in servers:
            self.consumed.add(id(s))
        if order:
            tokens = [t for s in order for t in s.path[2:]]
            methods = StrListSetting.known(list(dict.fromkeys(_AUTH_ORDER_MAP.get(t, t) for t in tokens)),
                                           [self.ev(s) for s in order])
        else:
            methods = StrListSetting.unknown(UnknownReason.NOT_FOUND, note="'system authentication-order' not set.")
        if order or servers:
            aaa = BoolSetting.known(True, [self.ev(s) for s in order] or [self.shortest(servers)],
                                    "Junos has no 'aaa new-model'; True means authentication-order or RADIUS/TACACS+ is configured.")
        else:
            aaa = BoolSetting.unknown(UnknownReason.NOT_FOUND, note="No authentication-order or RADIUS/TACACS+ servers found.")
        return AuthenticationSettings(
            aaa_enabled=aaa, methods=methods,
            password_encryption_service=BoolSetting.unknown(
                UnknownReason.UNSUPPORTED, note="Junos always stores secrets hashed or obfuscated; no equivalent setting."),
            privileged_credential_storage=self.root_credential(),
            local_user_credential_storage=self.local_users(),
        )

    def root_credential(self) -> StrSetting:
        found = self.find("system", "root-authentication", "encrypted-password", "*")
        if not found:
            return StrSetting.unknown(UnknownReason.NOT_FOUND, note="No root-authentication encrypted-password found.")
        storage = classify_junos_hash(found[-1].path[3])
        if storage is None:
            return StrSetting.unknown(UnknownReason.UNRECOGNIZED, [self.ev(found[-1])], "Unrecognized password hash format.")
        return StrSetting.known(storage, [self.ev(found[-1])])

    def local_users(self) -> StrListSetting:
        found = self.find("system", "login", "user", "*", "authentication", "encrypted-password", "*")
        if not found:
            return StrListSetting.unknown(UnknownReason.NOT_FOUND, note="No local users with encrypted-password found.")
        algos: set[str] = set()
        for s in found:
            storage = classify_junos_hash(s.path[6])
            if storage:
                algos.add(storage)
            else:
                self.warnings.append(ParseWarning(code="unrecognized_hash", line_number=s.number,
                                                  message="Unrecognized local user password hash format."))
        evidence = [self.ev(s) for s in found]
        if not algos:
            return StrListSetting.unknown(UnknownReason.UNRECOGNIZED, evidence)
        return StrListSetting.known(sorted(algos), evidence)

    # -- logging / ntp
    def logging(self) -> LoggingSettings:
        found = [s for s in self.find("system", "syslog", "host", "*")]
        self.claim("system", "syslog", "host")
        if not found:
            return LoggingSettings(remote_hosts=StrListSetting.unknown(UnknownReason.NOT_FOUND,
                                                                       note="No 'system syslog host' found."))
        hosts = list(dict.fromkeys(s.path[3] for s in found))
        first_per_host = [min((s for s in found if s.path[3] == h), key=lambda s: (len(s.path), s.number)) for h in hosts]
        return LoggingSettings(remote_hosts=StrListSetting.known(hosts, [self.ev(s) for s in first_per_host]))

    def ntp(self) -> NtpSettings:
        servers = self.find("system", "ntp", "server", "*")
        self.claim("system", "ntp", "server")
        self.claim("system", "ntp", "authentication-key")
        self.claim("system", "ntp", "trusted-key")
        if not servers:
            note = "No 'system ntp server' found."
            return NtpSettings(servers=StrListSetting.unknown(UnknownReason.NOT_FOUND, note=note),
                               authentication_enabled=BoolSetting.unknown(UnknownReason.NOT_FOUND, note=note))
        names = list(dict.fromkeys(s.path[3] for s in servers))
        keyed = self.find("system", "ntp", "server", "*", "key", "*")
        keys = self.find("system", "ntp", "authentication-key", "*")
        if keyed and keys:
            auth = BoolSetting.known(True, [self.ev(s) for s in keyed[:1] + keys[:1]],
                                     "Key IDs and trusted-key status are not cross-checked.")
        else:
            auth = BoolSetting.known(False, [self.shortest(servers)],
                                     "No NTP server references an authentication key.")
        firsts = [min((s for s in servers if s.path[3] == n), key=lambda s: (len(s.path), s.number)) for n in names]
        return NtpSettings(servers=StrListSetting.known(names, [self.ev(s) for s in firsts]),
                           authentication_enabled=auth)

    # -- snmp
    def snmp(self) -> SnmpSettings:
        all_snmp = self.find("snmp")
        if not all_snmp:
            note = "No 'snmp' configuration found."
            return SnmpSettings(versions=StrListSetting.unknown(UnknownReason.NOT_FOUND, note=note),
                                v3_min_security_level=StrSetting.unknown(UnknownReason.NOT_FOUND, note=note),
                                default_community_in_use=BoolSetting.unknown(UnknownReason.NOT_FOUND, note=note))
        communities = [s for s in self.find("snmp", "community", "*")]
        v3 = self.find("snmp", "v3")
        self.claim("snmp", "community")
        self.claim("snmp", "v3")
        names = {s.path[2] for s in communities}
        versions = (["v1/v2c"] if communities else []) + (["v3"] if v3 else [])
        first_community = [min((s for s in communities if s.path[2] == n), key=lambda s: (len(s.path), s.number))
                           for n in sorted(names)]
        version_ev = [self.ev(s) for s in first_community] + ([self.shortest(v3)] if v3 else [])
        default_hits = [s for s in first_community if s.path[2].lower() in ("public", "private")]
        if first_community:
            default = BoolSetting.known(bool(default_hits), [self.ev(s) for s in (default_hits or first_community)])
        else:
            default = BoolSetting.known(False, [self.shortest(all_snmp)], "No SNMP communities configured.")
        return SnmpSettings(
            versions=StrListSetting.known(versions, version_ev) if versions else StrListSetting.known(
                [], [self.shortest(all_snmp)], "SNMP configured without communities or v3."),
            v3_min_security_level=self.v3_level(),
            default_community_in_use=default,
        )

    def v3_level(self) -> StrSetting:
        users: dict[str, set[str]] = {}
        stmts: dict[str, Stmt] = {}
        for s in self.find("snmp", "v3", "usm", "local-engine", "user", "*"):
            users.setdefault(s.path[5], set()).update(s.path[6:])
            stmts.setdefault(s.path[5], s)
        if not users:
            return StrSetting.unknown(UnknownReason.NOT_FOUND, note="No SNMPv3 USM users found.")
        levels: list[tuple[str, str]] = []
        for name, toks in users.items():
            level = "authPriv" if toks & _SNMP_PRIV else "authNoPriv" if toks & _SNMP_AUTH else "noAuthNoPriv"
            levels.append((level, name))
        worst = min(levels, key=lambda x: _LEVEL_RANK[x[0]])
        return StrSetting.known(worst[0], [self.ev(stmts[n]) for _, n in levels])

    # -- weaknesses + unknown commands
    def legacy_weaknesses(self) -> list[DetectedWeakness]:
        out: list[DetectedWeakness] = []
        for svc, label in _LEGACY_SERVICES.items():
            found = self.find("system", "services", svc)
            if found:
                out.append(DetectedWeakness(
                    identifier=f"{svc}-enabled", category="protocol",
                    description=f"The legacy/unencrypted service {label} is enabled.",
                    evidence=[self.shortest(found)]))
        return out

    def unknown_commands(self) -> list[UnknownCommand]:
        out: list[UnknownCommand] = []
        for s in self.stmts:
            if id(s) in self.consumed or not s.leaf:
                continue
            if not any(_matches(s.path, root) for root in _RELEVANT_ROOTS):
                continue
            if any(_matches(s.path, b) for b in _BENIGN):
                continue
            out.append(UnknownCommand(vendor=Vendor.JUNIPER_JUNOS, line_number=s.number,
                                      text="set " + " ".join(redact_junos_tokens(s.path))))
        return out


class JuniperJunosParser(BaseConfigParser):
    vendor = Vendor.JUNIPER_JUNOS
    name = "juniper_junos_parser"
    version = "0.1.0"

    _SIGNALS: list[tuple[str, re.Pattern[str]]] = [
        ("set-statements", re.compile(
            r"^set\s+(system|interfaces|protocols|security|firewall|routing-options|snmp|chassis|policy-options|vlans)\b", re.M)),
        ("system-block", re.compile(r"^system\s*\{", re.M)),
        ("junos-version", re.compile(r"^(set\s+)?version\s+\d+\.\d+[A-Za-z]\d", re.M)),
        ("last-commit-header", re.compile(r"^##\s*Last (commit|changed)", re.M)),
        ("interfaces-block", re.compile(r"^interfaces\s*\{", re.M)),
        ("junos-interface-names", re.compile(r"\b(?:ge|xe|et|fe)-\d+/\d+/\d+\b|\bfxp0\b|\bem0\b|\blo0\b")),
        ("host-name-statement", re.compile(r"^(?:set\s+system\s+)?\s*host-name\s+\S+", re.M)),
    ]

    def detection_signals(self, content: str) -> list[str]:
        return [name for name, rx in self._SIGNALS if rx.search(content)]

    def parse(self, content: str, vendor_hint: Vendor | None = None) -> ParseResult:
        stmts, warnings = parse_statements(content)
        if any(s.path[0] == "groups" for s in stmts) or any("apply-groups" in s.path for s in stmts):
            warnings.append(ParseWarning(
                code="groups_not_evaluated",
                message="Configuration groups are present; values inherited through apply-groups are not evaluated."))
        inactive = sum(1 for s in stmts if s.inactive and s.leaf)
        if inactive:
            warnings.append(ParseWarning(code="inactive_statements_ignored",
                                         message=f"{inactive} inactive/deactivated statement(s) were ignored."))
        ex = _Extractor(stmts)
        hostname = ex.find("system", "host-name")
        cfg = NormalizedConfig(
            vendor=Vendor.JUNIPER_JUNOS,
            hostname=StrSetting.known(hostname[-1].path[2], [ex.ev(hostname[-1])]) if len(hostname) and len(hostname[-1].path) > 2
            else StrSetting.unknown(UnknownReason.NOT_FOUND, note="No 'system host-name' found."),
            management=ex.management(),
            authentication=ex.authentication(),
            logging=ex.logging(),
            ntp=ex.ntp(),
            snmp=ex.snmp(),
        )
        cfg.detected_weak_settings = derive_weak_settings(cfg) + ex.legacy_weaknesses()
        warnings += ex.warnings
        if not ex.stmts:
            warnings.append(ParseWarning(code="no_statements", message="No configuration statements were found."))
        return ParseResult(
            parser_name=self.name, parser_version=self.version, schema_version=SCHEMA_VERSION,
            vendor=Vendor.JUNIPER_JUNOS, config=cfg, warnings=warnings,
            unknown_commands=ex.unknown_commands(), line_count=len(content.split("\n")),
        )
