"""Validation of uploaded configuration files. Uploads are untrusted input and are only ever
held in memory: nothing is written to disk and nothing is executed."""
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field

from app.core.config import Settings
from app.core.errors import AppError
from app.schemas.parsing import ParseWarning

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0e-\x1f\x7f]")


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str
    content: str
    size_bytes: int
    sha256: str
    line_count: int
    encoding: str
    warnings: list[ParseWarning] = field(default_factory=list)


def sanitize_filename(name: str | None) -> str:
    """Display-only name. It is never used to build a filesystem path."""
    base = os.path.basename((name or "").replace("\\", "/")).strip()
    base = _CONTROL_CHARS.sub("", base)[:255]
    return base or "uploaded-config"


def validate_upload(filename: str | None, data: bytes, settings: Settings) -> ValidatedUpload:
    if len(data) > settings.max_upload_bytes:
        raise AppError(413, "file_too_large",
                       f"File exceeds the {settings.max_upload_bytes // 1024} KB upload limit.",
                       {"max_bytes": settings.max_upload_bytes})
    if len(data) == 0:
        raise AppError(400, "empty_file", "The uploaded file is empty.")

    safe_name = sanitize_filename(filename)
    ext = os.path.splitext(safe_name)[1].lower()
    if ext and ext not in settings.allowed_extension_set:
        raise AppError(415, "unsupported_file_type",
                       f"Files of type '{ext}' are not accepted. Allowed: "
                       f"{', '.join(sorted(settings.allowed_extension_set))} (or no extension).",
                       {"allowed_extensions": sorted(settings.allowed_extension_set)})

    if b"\x00" in data or len(_CONTROL_CHARS.findall(data.decode("latin-1"))) > max(8, len(data) // 50):
        raise AppError(415, "binary_file", "The file looks like binary data, not a text configuration.")

    warnings: list[ParseWarning] = []
    try:
        text, encoding = data.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        text, encoding = data.decode("latin-1"), "latin-1"
        warnings.append(ParseWarning(code="non_utf8_encoding",
                                     message="File is not valid UTF-8; decoded as Latin-1."))

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        raise AppError(400, "empty_file", "The uploaded file contains only whitespace.")

    lines = text.split("\n")
    if len(lines) > settings.max_lines:
        raise AppError(413, "too_many_lines", f"File has more than {settings.max_lines} lines.")
    for number, line in enumerate(lines, start=1):
        if len(line) > settings.max_line_length:
            raise AppError(400, "malformed_file",
                           f"Line {number} is longer than {settings.max_line_length} characters; "
                           "this does not look like a device configuration.",
                           {"line_number": number})

    return ValidatedUpload(
        filename=safe_name, content=text, size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(), line_count=len(lines),
        encoding=encoding, warnings=warnings,
    )
