"""Orchestrates: validated upload -> vendor resolution -> parsing -> normalized result.

Phase 2/3 scope: no persistence yet (Phase 6 adds audits, rules and storage)."""
from __future__ import annotations

import logging

from app.core.errors import AppError
from app.parsers.registry import VENDOR_DISPLAY_NAMES, get_parser, supported_vendors
from app.schemas.api import ConfigParseResponse, FileInfo
from app.schemas.detection import Confidence, VendorDetection
from app.schemas.normalized import Vendor
from app.schemas.parsing import ParseWarning
from app.services.upload_validation import ValidatedUpload
from app.services.vendor_detection import detect_vendor

log = logging.getLogger("netaudit.pipeline")


def _supported_names() -> str:
    return ", ".join(VENDOR_DISPLAY_NAMES[v] for v in supported_vendors())


def resolve_vendor(content: str, requested: str, force: bool) -> tuple[Vendor, VendorDetection, list[ParseWarning]]:
    detection = detect_vendor(content)
    warnings: list[ParseWarning] = []

    if requested == "auto":
        if detection.detected_vendor is None or detection.confidence == Confidence.LOW:
            raise AppError(422, "vendor_undetected",
                           "Could not confidently detect the vendor. Please select it explicitly.",
                           {"detection": detection.model_dump(mode="json")})
        if not detection.supported:
            raise AppError(422, "vendor_unsupported",
                           f"Detected {VENDOR_DISPLAY_NAMES[detection.detected_vendor]}, which is not supported yet. "
                           f"Supported vendors: {_supported_names()}.",
                           {"detection": detection.model_dump(mode="json")})
        return detection.detected_vendor, detection, warnings

    try:
        vendor = Vendor(requested)
    except ValueError:
        raise AppError(422, "invalid_vendor", f"Unknown vendor '{requested[:40]}'.",
                       {"valid": ["auto"] + [v.value for v in Vendor]}) from None
    parser = get_parser(vendor)
    if parser is None:
        raise AppError(422, "vendor_unsupported",
                       f"{VENDOR_DISPLAY_NAMES[vendor]} is not supported yet. Supported vendors: {_supported_names()}.")
    if (not force and detection.detected_vendor not in (None, vendor)
            and detection.confidence == Confidence.HIGH):
        raise AppError(422, "vendor_mismatch",
                       f"You selected {VENDOR_DISPLAY_NAMES[vendor]}, but the file strongly resembles "
                       f"{VENDOR_DISPLAY_NAMES[detection.detected_vendor]}. Choose 'auto' or set force_vendor to override.",
                       {"detection": detection.model_dump(mode="json")})
    if not parser.can_parse(content, vendor):
        raise AppError(422, "vendor_content_mismatch",
                       f"The file does not look like {VENDOR_DISPLAY_NAMES[vendor]} configuration.",
                       {"detection": detection.model_dump(mode="json")})
    if force and detection.detected_vendor not in (None, vendor):
        warnings.append(ParseWarning(code="vendor_override",
                                     message="Vendor was forced and differs from the detected vendor."))
    return vendor, detection, warnings


def analyze_config(upload: ValidatedUpload, requested_vendor: str = "auto", force: bool = False) -> ConfigParseResponse:
    vendor, detection, warnings = resolve_vendor(upload.content, requested_vendor, force)
    parser = get_parser(vendor)
    assert parser is not None
    try:
        result = parser.parse(upload.content, vendor)
    except Exception as exc:  # parsers must not crash the API; never log config content
        log.error("parser_failure vendor=%s sha256=%s error=%s", vendor.value, upload.sha256, type(exc).__name__)
        raise AppError(500, "parser_failure", "The parser failed to process this file.") from None
    log.info("parsed vendor=%s sha256=%s lines=%d unknown_commands=%d",
             vendor.value, upload.sha256, upload.line_count, len(result.unknown_commands))
    return ConfigParseResponse(
        file=FileInfo(filename=upload.filename, size_bytes=upload.size_bytes, sha256=upload.sha256,
                      line_count=upload.line_count, encoding=upload.encoding),
        requested_vendor=requested_vendor, vendor_used=vendor, detection=detection, result=result,
        warnings=upload.warnings + warnings,
    )
