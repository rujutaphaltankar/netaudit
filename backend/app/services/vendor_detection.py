"""Heuristic vendor detection. Supported vendors use their parser's own signals; recognised but
unsupported vendors use signatures defined here so users get a clear 'not supported yet' message."""
from __future__ import annotations

import re

from app.parsers.registry import all_parsers
from app.schemas.detection import Confidence, VendorDetection
from app.schemas.normalized import Vendor

_UNSUPPORTED_SIGNATURES: dict[Vendor, list[tuple[str, re.Pattern[str]]]] = {
    Vendor.PALO_ALTO_PANOS: [
        ("set-deviceconfig", re.compile(r"^set\s+deviceconfig\s+system\b", re.M)),
        ("set-rulebase", re.compile(r"^set\s+rulebase\s+security\b|^set\s+(shared|zone|network)\s", re.M)),
        ("set-mgt-config", re.compile(r"^set\s+mgt-config\b", re.M)),
        ("panos-xml", re.compile(r"<config\s+version=.*<devices>", re.S)),
    ],
    Vendor.FORTINET_FORTIOS: [
        ("config-system", re.compile(r"^config\s+system\s+\w+", re.M)),
        ("config-firewall", re.compile(r"^config\s+(firewall|router|vpn|user)\s+\w+", re.M)),
        ("fg-header", re.compile(r"^#config-version=FG", re.M)),
        ("next-end", re.compile(r"^\s*next\s*$", re.M)),
    ],
    Vendor.ARISTA_EOS: [
        ("device-header", re.compile(r"^!\s*device:\s*\S+\s*\(.*EOS", re.M)),
        ("http-commands", re.compile(r"^management\s+api\s+http-commands", re.M)),
        ("ethernet-interfaces", re.compile(r"^interface\s+Ethernet\d+", re.M)),
        ("daemon", re.compile(r"^daemon\s+\S+", re.M)),
        ("transceiver", re.compile(r"^transceiver\s+qsfp\s+default-mode", re.M)),
    ],
}


def detect_vendor(content: str) -> VendorDetection:
    signals: dict[Vendor, list[str]] = {}
    for parser in all_parsers():
        signals[parser.vendor] = parser.detection_signals(content)
    for vendor, sigs in _UNSUPPORTED_SIGNATURES.items():
        signals[vendor] = [name for name, rx in sigs if rx.search(content)]

    scores = {v.value: len(s) for v, s in signals.items()}
    ranked = sorted(signals.items(), key=lambda kv: len(kv[1]), reverse=True)
    top_vendor, top_signals = ranked[0]
    top = len(top_signals)
    runner_up = len(ranked[1][1]) if len(ranked) > 1 else 0

    if top == 0 or top == runner_up:
        # No evidence, or a tie: refuse to guess.
        return VendorDetection(scores=scores, signals=[])
    if top >= 4 and top - runner_up >= 3:
        confidence = Confidence.HIGH
    elif top >= 2 and top > runner_up:
        confidence = Confidence.MEDIUM
    else:
        confidence = Confidence.LOW
    supported = top_vendor in {p.vendor for p in all_parsers()}
    return VendorDetection(detected_vendor=top_vendor, confidence=confidence, supported=supported,
                           signals=top_signals, scores=scores)
