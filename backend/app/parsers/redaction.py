"""Secret redaction for evidence text. Evidence is redacted *before* it is stored or logged."""
from __future__ import annotations

import re

REDACTED = "<redacted>"

# Ordered specific -> generic. Only the first rule that changes a line is applied.
_CISCO_RULES: list[re.Pattern[str]] = [re.compile(p, re.IGNORECASE) for p in (
    r"^(\s*enable\s+(?:secret|password)\s+(?:level\s+\d+\s+)?(?:\d\s+)?)\S+",
    r"^(\s*snmp-server\s+community\s+)\S+",
    r"^(\s*snmp-server\s+host\s+\S+\s+(?:(?:informs?|traps?|version\s+\S+)\s+)*(?:(?:auth|priv|noauth)\s+)?)\S+",
    r"(\b(?:auth|priv)\s+(?:md5|sha256|sha384|sha512|sha|3des|des|aes(?:\s+(?:128|192|256))?)\s+)\S+",
    r"^(\s*ntp\s+authentication-key\s+\d+\s+\S+\s+)\S+",
    r"^(\s*(?:radius-server|tacacs-server)\b.*?\bkey\s+(?:\d\s+)?)\S+",
    r"^(\s*crypto\s+isakmp\s+key\s+(?:\d\s+)?)\S+",
    r"(\bmessage-digest-key\s+\d+\s+md5\s+(?:\d\s+)?)\S+",
    r"^(\s*(?:pac\s+)?key\s+\d\s+)\S+",
    r"^(\s*(?:pac\s+)?key\s+)(?!\d+\s*$)\S+\s*$",
    r"^(\s*key-string\s+(?:\d\s+)?)\S+",
    r"(\b(?:secret|password)\s+(?:\d\s+)?)\S+",
)]


def redact_cisco_line(text: str) -> str:
    for rule in _CISCO_RULES:
        new = rule.sub(r"\1" + REDACTED, text)
        if new != text:
            return new
    return text


_JUNOS_SECRET_KEYWORDS = {
    "encrypted-password", "plain-text-password-value", "authentication-password",
    "privacy-password", "secret", "value", "key-string", "simple-password",
}


def redact_junos_tokens(tokens: tuple[str, ...] | list[str]) -> list[str]:
    """Redact secret-bearing tokens in a Junos statement path.

    Decisions are made against the ORIGINAL tokens so that redacting one token can never
    expose the token that follows it.
    """
    original = list(tokens)
    out = list(original)
    for i, tok in enumerate(original):
        prev = original[i - 1] if i > 0 else ""
        if prev in _JUNOS_SECRET_KEYWORDS:
            out[i] = REDACTED
        elif prev == "community" and original[0] == "snmp":
            out[i] = REDACTED
        elif prev == "key" and "authentication" in original[:i]:
            out[i] = REDACTED  # e.g. OSPF 'authentication md5 1 key <secret>'
    return out
