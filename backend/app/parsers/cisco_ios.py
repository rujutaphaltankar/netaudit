"""Cisco IOS-style configuration parser (parser version 0.1.0)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.parsers.base import BaseConfigParser
from app.parsers.redaction import redact_cisco_line
from app.parsers.weakness import derive_weak_settings
from app.schemas.normalized import (
    SCHEMA_VERSION, AuthenticationSettings, BoolSetting, CredentialStorage, DetectedWeakness,
    Evidence, FloatSetting, LoggingSettings, ManagementSettings, NormalizedConfig, NtpSettings,
    SnmpSettings, StrListSetting, StrSetting, UnknownReason, Vendor,
)
from app.schemas.parsing import ParseResult, ParseWarning, UnknownCommand

# --------------------------------------------------------------------------- tokenizing

@dataclass(frozen=True)
class Line:
    number: int
    text: str
    indent: int
    context: str | None  # text of the enclosing top-level line, if any


@dataclass
class Block:
    header: Line
    children: list[Line] = field(default_factory=list)


_BANNER_RE = re.compile(r"^banner\s+(\S+)\s+(\S+)(.*)$", re.IGNORECASE)


def tokenize(content: str) -> list[Line]:
    """Split IOS text into meaningful lines, skipping comments and banner bodies."""
    lines: list[Line] = []
    header: str | None = None
    banner_delim: str | None = None
    for number, raw in enumerate(content.split("\n"), start=1):
        raw = raw.rstrip("\r").expandtabs(4)
        if banner_delim is not None:
            if banner_delim in raw:
                banner_delim = None
            continue
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("!"):
            header = None
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent == 0:
            m = _BANNER_RE.match(stripped)
            if m:
                delim = "^C" if m.group(2).startswith("^C") else m.group(2)[0]
                rest = m.group(2)[len(delim):] + m.group(3)
                if delim not in rest:
                    banner_delim = delim
                header = None
                continue
        context = None if indent == 0 else header
        lines.append(Line(number, stripped, indent, context))
        if indent == 0:
            header = stripped
    return lines


# --------------------------------------------------------------------------- unknown-command policy

_SECURITY_RELEVANT = re.compile(
    r"^(no\s+)?(aaa|snmp-server|ntp|logging|ip\s+ssh|ip\s+http|service|enable|username|line|"
    r"radius|tacacs|crypto|login|security)\b", re.IGNORECASE)

_BENIGN = [re.compile(p, re.IGNORECASE) for p in (
    r"^(no\s+)?service\s+(timestamps|sequence-numbers|call-home|compress-config|pad)\b",
    r"^logging\s+(buffered|trap|console|monitor|on|source-interface|facility|origin-id|rate-limit|"
    r"count|persistent|discriminator|userinfo|queue-limit)\b",
    r"^ntp\s+(authentication-key|trusted-key|authenticate|source)\b",
    r"^snmp-server\s+(location|contact|host|enable|trap-source|chassis-id|ifindex|engineID|view)\b",
    r"^(logging\s+synchronous|login(\s+local)?|login\s+authentication\s+\S+|privilege\s+level\s+\d+|"
    r"length\s+\d+|width\s+\d+|exec-timeout\s+\d+(\s+\d+)?|no\s+exec-timeout|password\s+.*|"
    r"stopbits\s+\d|speed\s+\d+)$",
)]

_ACL_HEADER = re.compile(r"^(ip(v6)?\s+access-list|access-list)\b", re.IGNORECASE)
_VTY = re.compile(r"^line\s+vty\b", re.IGNORECASE)
_LINE_BLOCK = re.compile(r"^line\s+(vty|con|aux|\d)", re.IGNORECASE)

_TYPE_TO_STORAGE = {
    "0": CredentialStorage.CLEARTEXT, "4": CredentialStorage.SHA256_UNSALTED,
    "5": CredentialStorage.MD5, "7": CredentialStorage.REVERSIBLE,
    "8": CredentialStorage.PBKDF2_SHA256, "9": CredentialStorage.SCRYPT,
}
_WEAK_SSH_ALGOS = {"3des-cbc", "aes128-cbc", "aes192-cbc", "aes256-cbc", "hmac-md5", "hmac-md5-96",
                   "hmac-sha1-96", "diffie-hellman-group1-sha1"}
_SNMP_LEVEL_RANK = {"noAuthNoPriv": 0, "authNoPriv": 1, "authPriv": 2}


class _Extractor:
    def __init__(self, lines: list[Line]) -> None:
        self.lines = lines
        self.consumed: set[int] = set()
        self.top = [ln for ln in lines if ln.context is None]
        self.blocks: list[Block] = []
        current: Block | None = None
        for ln in lines:
            if ln.context is None:
                current = Block(ln)
                self.blocks.append(current)
            elif current is not None:
                current.children.append(ln)
        self.warnings: list[ParseWarning] = []

    # -- helpers
    def ev(self, line: Line) -> Evidence:
        self.consumed.add(line.number)
        return Evidence(line_number=line.number, text=redact_cisco_line(line.text), context=line.context)

    def top_matches(self, pattern: str) -> list[tuple[Line, re.Match[str]]]:
        rx = re.compile(pattern, re.IGNORECASE)
        return [(ln, m) for ln in self.top if (m := rx.match(ln.text))]

    def last(self, pattern: str) -> tuple[Line, re.Match[str]] | None:
        found = self.top_matches(pattern)
        return found[-1] if found else None

    def vty_blocks(self) -> list[Block]:
        blocks = [b for b in self.blocks if _VTY.match(b.header.text)]
        for b in blocks:
            self.consumed.add(b.header.number)
        return blocks

    # -- simple flags
    def _flag(self, base: str, note: str) -> BoolSetting:
        pos = self.last(rf"{base}\s*$")
        neg = self.last(rf"no\s+{base}\s*$")
        candidates = [x for x in (pos, neg) if x]
        if not candidates:
            return BoolSetting.unknown(UnknownReason.NOT_FOUND, note=note)
        line, _ = max(candidates, key=lambda x: x[0].number)
        return BoolSetting.known(line.text.lower().startswith("no ") is False, [self.ev(line)])

    # -- management
    def management(self) -> ManagementSettings:
        vty = self.vty_blocks()
        return ManagementSettings(
            ssh_enabled=self._transport_flag(vty, "ssh"),
            ssh_version=self._ssh_version(),
            telnet_enabled=self._transport_flag(vty, "telnet"),
            http_enabled=self._flag(r"ip\s+http\s+server", "'ip http server' not present; default varies by IOS version."),
            https_enabled=self._flag(r"ip\s+http\s+secure-server", "'ip http secure-server' not present."),
            admin_acls=self._admin_acls(vty),
            session_timeout_minutes=self._timeout(vty),
        )

    @staticmethod
    def _transport(block: Block) -> tuple[Line, set[str]] | None:
        found = [c for c in block.children if re.match(r"transport\s+input\s+", c.text, re.IGNORECASE)]
        if not found:
            return None
        return found[-1], set(found[-1].text.lower().split()[2:])

    def _transport_flag(self, vty: list[Block], proto: str) -> BoolSetting:
        if not vty:
            return BoolSetting.unknown(UnknownReason.NOT_FOUND, note="No 'line vty' block found.")
        enabled: list[Evidence] = []
        disabled: list[Evidence] = []
        unspecified: list[Evidence] = []
        for b in vty:
            t = self._transport(b)
            if t is None:
                unspecified.append(self.ev(b.header))
            elif proto in t[1] or "all" in t[1]:
                enabled.append(self.ev(t[0]))
            else:
                disabled.append(self.ev(t[0]))
        if enabled:
            return BoolSetting.known(True, enabled)
        if unspecified:
            return BoolSetting.unknown(
                UnknownReason.AMBIGUOUS, unspecified,
                "'transport input' is not configured on every vty line; the default depends on the IOS version.")
        return BoolSetting.known(False, disabled)

    def _ssh_version(self) -> StrSetting:
        found = self.last(r"ip\s+ssh\s+version\s+(\d)\s*$")
        if not found:
            return StrSetting.unknown(UnknownReason.NOT_FOUND,
                                      note="'ip ssh version' not set; the default depends on IOS version and keys.")
        line, m = found
        return StrSetting.known(m.group(1), [self.ev(line)])

    def _admin_acls(self, vty: list[Block]) -> StrListSetting:
        if not vty:
            return StrListSetting.unknown(UnknownReason.NOT_FOUND, note="No 'line vty' block found.")
        per_block: list[set[str]] = []
        evidence: list[Evidence] = []
        for b in vty:
            names: set[str] = set()
            for c in b.children:
                m = re.match(r"(?:ipv6\s+)?access-class\s+(\S+)\s+in\b", c.text, re.IGNORECASE)
                if m:
                    names.add(m.group(1))
                    evidence.append(self.ev(c))
            per_block.append(names)
        if not evidence:
            evidence = [self.ev(b.header) for b in vty]
        common = set.intersection(*per_block)
        with_acl = sum(1 for n in per_block if n)
        return StrListSetting.known(
            sorted(common), evidence,
            f"Inbound ACL present on {with_acl} of {len(vty)} vty block(s); ACL contents are not evaluated.")

    def _timeout(self, vty: list[Block]) -> FloatSetting:
        if not vty:
            return FloatSetting.unknown(UnknownReason.NOT_FOUND, note="No 'line vty' block found.")
        values: list[float] = []
        evidence: list[Evidence] = []
        missing: list[Evidence] = []
        for b in vty:
            hit = None
            for c in b.children:
                m = re.match(r"exec-timeout\s+(\d+)(?:\s+(\d+))?\s*$", c.text, re.IGNORECASE)
                if m:
                    hit = (c, int(m.group(1)) + int(m.group(2) or 0) / 60)
                elif re.match(r"no\s+exec-timeout\s*$", c.text, re.IGNORECASE):
                    hit = (c, 0.0)
            if hit:
                values.append(hit[1])
                evidence.append(self.ev(hit[0]))
            else:
                missing.append(self.ev(b.header))
        if any(v == 0 for v in values):
            return FloatSetting.known(0.0, evidence, "At least one vty block never times out (exec-timeout 0).")
        if missing:
            return FloatSetting.unknown(
                UnknownReason.AMBIGUOUS, evidence + missing,
                "exec-timeout is not set on every vty block; the IOS default applies there.")
        return FloatSetting.known(round(max(values), 2), evidence)

    # -- authentication
    def authentication(self) -> AuthenticationSettings:
        aaa = self._flag(r"aaa\s+new-model", "'aaa new-model' not present.")
        return AuthenticationSettings(
            aaa_enabled=aaa,
            methods=self._auth_methods(),
            password_encryption_service=self._flag(r"service\s+password-encryption",
                                                   "'service password-encryption' not present."),
            privileged_credential_storage=self._enable_secret(),
            local_user_credential_storage=self._local_users(),
        )

    def _auth_methods(self) -> StrListSetting:
        found = self.top_matches(r"aaa\s+authentication\s+login\s+(\S+)\s+(.+)$")
        if not found:
            return StrListSetting.unknown(UnknownReason.NOT_FOUND, note="No 'aaa authentication login' line found.")
        default = [f for f in found if f[1].group(1).lower() == "default"] or found
        methods: list[str] = []
        tokens = " ".join(m.group(2) for _, m in default).split()
        i = 0
        while i < len(tokens):
            t = tokens[i].lower()
            if t == "group" and i + 1 < len(tokens):
                g = tokens[i + 1].lower()
                methods.append(g if g in ("radius", "tacacs+") else f"group:{tokens[i + 1]}")
                i += 2
                continue
            methods.append("local" if t in ("local", "local-case") else t)
            i += 1
        ordered = list(dict.fromkeys(methods))
        note = None if len(default) == len(found) and default[0][1].group(1).lower() == "default" \
            else "No 'default' list found; methods combined from named lists."
        return StrListSetting.known(ordered, [self.ev(ln) for ln, _ in default], note)

    def _enable_secret(self) -> StrSetting:
        secret = self.last(r"enable\s+secret\s+(?:level\s+\d+\s+)?(?:(\d)\s+)?\S+")
        password = self.last(r"enable\s+password\s+(?:level\s+\d+\s+)?(?:(\d)\s+)?\S+")
        if secret:
            line, m = secret
            storage = _TYPE_TO_STORAGE.get(m.group(1) or "")
            evidence = [self.ev(line)] + ([self.ev(password[0])] if password else [])
            if storage is None:
                return StrSetting.unknown(UnknownReason.AMBIGUOUS, evidence,
                                          "Hash type of 'enable secret' is not shown or not recognized.")
            return StrSetting.known(storage, evidence,
                                    "'enable secret' takes precedence over 'enable password'." if password else None)
        if password:
            line, m = password
            return StrSetting.known(_TYPE_TO_STORAGE.get(m.group(1) or "0", CredentialStorage.CLEARTEXT), [self.ev(line)])
        return StrSetting.unknown(UnknownReason.NOT_FOUND, note="No 'enable secret' or 'enable password' found.")

    def _local_users(self) -> StrListSetting:
        users = self.top_matches(r"username\s+\S+\b.*$")
        if not users:
            return StrListSetting.unknown(UnknownReason.NOT_FOUND, note="No local 'username' entries found.")
        algos: set[str] = set()
        evidence: list[Evidence] = []
        ambiguous = 0
        for line, _ in users:
            text = line.text
            m = re.search(r"\b(secret|password)\s+(?:(\d)\s+)?\S+", text, re.IGNORECASE)
            evidence.append(self.ev(line))
            if re.search(r"\bnopassword\b", text, re.IGNORECASE):
                algos.add(CredentialStorage.NONE)
            elif m and m.group(2):
                algos.add(_TYPE_TO_STORAGE.get(m.group(2), "unrecognized"))
            elif m and m.group(1).lower() == "password":
                algos.add(CredentialStorage.CLEARTEXT)
            elif m:
                ambiguous += 1
                self.warnings.append(ParseWarning(code="ambiguous_user_secret", line_number=line.number,
                                                  message="Local user secret type is not shown; skipped."))
        algos.discard("unrecognized")
        if not algos:
            return StrListSetting.unknown(UnknownReason.AMBIGUOUS if ambiguous else UnknownReason.UNRECOGNIZED, evidence,
                                          "Could not determine credential storage for local users.")
        return StrListSetting.known(sorted(algos), evidence)

    # -- logging / ntp
    def logging(self) -> LoggingSettings:
        hosts: list[str] = []
        evidence: list[Evidence] = []
        for line, _ in self.top_matches(r"logging\s+(?:host\s+)?(\S.*)$"):
            toks = line.text.split()[1:]
            if toks and toks[0].lower() == "host":
                toks = toks[1:]
                if toks and toks[0].lower() == "vrf":
                    toks = toks[2:]
                if toks and toks[0].lower() == "ipv6":
                    toks = toks[1:]
            elif not re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", toks[0] if toks else ""):
                continue
            if toks:
                hosts.append(toks[0])
                evidence.append(self.ev(line))
        if not hosts:
            return LoggingSettings(remote_hosts=StrListSetting.unknown(
                UnknownReason.NOT_FOUND, note="No remote syslog host found."))
        return LoggingSettings(remote_hosts=StrListSetting.known(list(dict.fromkeys(hosts)), evidence))

    def ntp(self) -> NtpSettings:
        servers = self.top_matches(r"ntp\s+(?:server|peer)\s+(?:vrf\s+\S+\s+)?(\S+)")
        if not servers:
            return NtpSettings(servers=StrListSetting.unknown(UnknownReason.NOT_FOUND, note="No 'ntp server' found."),
                               authentication_enabled=self._flag(r"ntp\s+authenticate", "'ntp authenticate' not present."))
        return NtpSettings(
            servers=StrListSetting.known(list(dict.fromkeys(m.group(1) for _, m in servers)),
                                         [self.ev(ln) for ln, _ in servers]),
            authentication_enabled=self._flag(r"ntp\s+authenticate", "'ntp authenticate' not present."),
        )

    # -- snmp
    def snmp(self) -> SnmpSettings:
        communities = self.top_matches(r"snmp-server\s+community\s+(\S+)")
        groups = self.top_matches(r"snmp-server\s+group\s+\S+\s+v3\s+(auth|priv|noauth)\b")
        users = self.top_matches(r"snmp-server\s+user\s+\S+\s+\S+\s+v3\b.*")
        if not (communities or groups or users):
            note = "No SNMP community/group/user lines found."
            return SnmpSettings(versions=StrListSetting.unknown(UnknownReason.NOT_FOUND, note=note),
                                v3_min_security_level=StrSetting.unknown(UnknownReason.NOT_FOUND, note=note),
                                default_community_in_use=BoolSetting.unknown(UnknownReason.NOT_FOUND, note=note))
        versions: list[str] = []
        if communities:
            versions.append("v1/v2c")
        if groups or users:
            versions.append("v3")
        default_ev = [self.ev(ln) for ln, m in communities if m.group(1).lower() in ("public", "private")]
        community_ev = [self.ev(ln) for ln, _ in communities]
        version_ev = community_ev + [self.ev(ln) for ln, _ in groups + users]

        level: StrSetting
        levels: list[tuple[str, Line]] = []
        for ln, m in groups:
            levels.append(({"noauth": "noAuthNoPriv", "auth": "authNoPriv", "priv": "authPriv"}[m.group(1).lower()], ln))
        if not groups:
            for ln, _ in users:
                t = f" {ln.text.lower()} "
                levels.append(("authPriv" if " priv " in t else "authNoPriv" if " auth " in t else "noAuthNoPriv", ln))
        if levels:
            worst = min(levels, key=lambda x: _SNMP_LEVEL_RANK[x[0]])
            level = StrSetting.known(worst[0], [self.ev(ln) for _, ln in levels])
        else:
            level = StrSetting.unknown(UnknownReason.NOT_FOUND, note="No SNMPv3 group/user found.")
        return SnmpSettings(
            versions=StrListSetting.known(versions, version_ev),
            v3_min_security_level=level,
            default_community_in_use=BoolSetting.known(bool(default_ev), default_ev or version_ev),
        )

    # -- misc consumption + extra weaknesses
    def consume_known_structures(self) -> list[DetectedWeakness]:
        for b in self.blocks:
            if _ACL_HEADER.match(b.header.text):
                self.consumed.add(b.header.number)
                self.consumed.update(c.number for c in b.children)
            elif _LINE_BLOCK.match(b.header.text):
                self.consumed.add(b.header.number)
        weak: list[DetectedWeakness] = []
        bad: list[Evidence] = []
        for line, m in self.top_matches(r"ip\s+ssh\s+server\s+algorithm\s+(?:encryption|mac|kex|hostkey)\s+(.+)$"):
            hits = sorted(t for t in m.group(1).lower().split() if t in _WEAK_SSH_ALGOS)
            if hits:
                bad.append(self.ev(line))
            else:
                self.ev(line)
        if bad:
            weak.append(DetectedWeakness(identifier="weak-ssh-algorithms", category="crypto",
                                         description="Legacy SSH algorithms are explicitly permitted.", evidence=bad))
        return weak

    def unknown_commands(self) -> list[UnknownCommand]:
        out: list[UnknownCommand] = []
        for ln in self.lines:
            if ln.number in self.consumed:
                continue
            header = ln.text if ln.context is None else ln.context
            if not _SECURITY_RELEVANT.match(header):
                continue
            if any(rx.match(ln.text) for rx in _BENIGN):
                continue
            out.append(UnknownCommand(vendor=Vendor.CISCO_IOS, line_number=ln.number,
                                      text=redact_cisco_line(ln.text), context=ln.context))
        return out


class CiscoIosParser(BaseConfigParser):
    vendor = Vendor.CISCO_IOS
    name = "cisco_ios_parser"
    version = "0.1.0"

    _SIGNALS: list[tuple[str, re.Pattern[str]]] = [
        ("hostname", re.compile(r"^hostname\s+\S+", re.M)),
        ("version", re.compile(r"^version\s+\d+\.\d+\S*\s*$", re.M)),
        ("service-commands", re.compile(r"^(no\s+)?service\s+(timestamps|password-encryption|tcp-keepalives\S*|pad)\b", re.M)),
        ("ios-interfaces", re.compile(
            r"^interface\s+(?:(?:Fast|Gigabit|TenGigabit|TwentyFiveGig|FortyGigabit|HundredGig)Ethernet|Loopback|Vlan|Port-channel|Serial|Tunnel)\S*", re.M)),
        ("line-blocks", re.compile(r"^line\s+(vty|con|aux)\b", re.M)),
        ("ios-security-commands", re.compile(
            r"^(aaa new-model|enable (secret|password)|ip ssh |ip http (secure-)?server|snmp-server |ntp server |logging (host|\d))", re.M)),
        ("config-header", re.compile(r"^(Building configuration|Current configuration\s*:)", re.M)),
    ]

    def detection_signals(self, content: str) -> list[str]:
        return [name for name, rx in self._SIGNALS if rx.search(content)]

    def parse(self, content: str, vendor_hint: Vendor | None = None) -> ParseResult:
        lines = tokenize(content)
        ex = _Extractor(lines)
        hostname = ex.last(r"hostname\s+(\S+)")
        cfg = NormalizedConfig(
            vendor=Vendor.CISCO_IOS,
            hostname=StrSetting.known(hostname[1].group(1), [ex.ev(hostname[0])]) if hostname
            else StrSetting.unknown(UnknownReason.NOT_FOUND, note="No 'hostname' line found."),
            management=ex.management(),
            authentication=ex.authentication(),
            logging=ex.logging(),
            ntp=ex.ntp(),
            snmp=ex.snmp(),
        )
        extra = ex.consume_known_structures()
        cfg.detected_weak_settings = derive_weak_settings(cfg) + extra
        warnings = list(ex.warnings)
        if not lines:
            warnings.append(ParseWarning(code="no_statements", message="No configuration statements were found."))
        return ParseResult(
            parser_name=self.name, parser_version=self.version, schema_version=SCHEMA_VERSION,
            vendor=Vendor.CISCO_IOS, config=cfg, warnings=warnings,
            unknown_commands=ex.unknown_commands(), line_count=len(content.split("\n")),
        )
