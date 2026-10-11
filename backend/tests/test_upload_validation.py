import hashlib

import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.services.upload_validation import sanitize_filename, validate_upload


def run(name, data, **overrides):
    return validate_upload(name, data, Settings(_env_file=None, **overrides))


def code(name, data, **overrides):
    with pytest.raises(AppError) as exc:
        run(name, data, **overrides)
    return exc.value.status_code, exc.value.code


def test_valid_file_metadata():
    data = b"hostname R1\r\nline vty 0 4\r\n"
    up = run("r1.cfg", data)
    assert up.sha256 == hashlib.sha256(data).hexdigest()
    assert "\r" not in up.content and up.line_count == 3 and up.encoding == "utf-8"


def test_empty_and_whitespace_only_rejected():
    assert code("a.cfg", b"") == (400, "empty_file")
    assert code("a.cfg", b"  \n\t\n") == (400, "empty_file")


def test_too_large():
    assert code("a.cfg", b"x" * 200, max_upload_bytes=100) == (413, "file_too_large")


def test_unsupported_extension():
    assert code("tool.exe", b"hostname R1") == (415, "unsupported_file_type")
    assert code("page.html", b"hostname R1") == (415, "unsupported_file_type")


def test_no_extension_allowed():
    assert run("running-config", b"hostname R1").filename == "running-config"


def test_binary_rejected():
    assert code("a.cfg", b"hostname R1\x00\x01\x02") == (415, "binary_file")
    assert code("a.cfg", bytes(range(0, 32)) * 20) == (415, "binary_file")


def test_overlong_line_rejected():
    status, c = code("a.cfg", b"hostname " + b"A" * 50, max_line_length=20)
    assert (status, c) == (400, "malformed_file")


def test_too_many_lines():
    assert code("a.cfg", b"a\n" * 50, max_lines=10) == (413, "too_many_lines")


def test_utf8_bom_is_handled():
    assert run("a.cfg", b"\xef\xbb\xbfhostname R1").content == "hostname R1"


def test_latin1_fallback_warns():
    up = run("a.cfg", "hostname caf\xe9".encode("latin-1"))
    assert up.encoding == "latin-1" and up.warnings[0].code == "non_utf8_encoding"


def test_filename_sanitized_against_traversal():
    assert sanitize_filename("../../etc/passwd.cfg") == "passwd.cfg"
    assert sanitize_filename("C:\\temp\\run.cfg") == "run.cfg"
    assert sanitize_filename(None) == "uploaded-config"
