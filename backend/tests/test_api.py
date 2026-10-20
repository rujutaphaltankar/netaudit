import hashlib

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from tests.conftest import read_sample, upload


def error_code(resp):
    return resp.json()["error"]["code"]


# ----------------------------------------------------------------------------- health / vendors
def test_health_is_public_and_reports_database(anon_client):
    body = anon_client.get("/api/v1/health").json()
    assert body["status"] == "ok" and body["database"] == "ok"
    assert body["ai_assistance"] == "fallback_only"


def test_health_with_reachable_database(tmp_path):
    s = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path / 'ok.db'}")
    app.dependency_overrides[get_settings] = lambda: s
    try:
        assert TestClient(app).get("/api/v1/health").json()["database"] == "ok"
    finally:
        app.dependency_overrides.clear()


def test_health_reports_unreachable_database():
    s = Settings(_env_file=None, database_url="sqlite:////nonexistent-dir/x/y.db")
    app.dependency_overrides[get_settings] = lambda: s
    try:
        assert TestClient(app).get("/api/v1/health").json()["database"] == "unavailable"
    finally:
        app.dependency_overrides.clear()


def test_postgres_urls_are_normalised():
    assert Settings(_env_file=None, database_url="postgres://u:p@h/db").database_url.startswith("postgresql+psycopg://")
    assert Settings(_env_file=None, database_url="postgresql://u:p@h/db").database_url.startswith("postgresql+psycopg://")


def test_vendors_listing(client):
    vendors = {v["id"]: v for v in client.get("/api/v1/vendors").json()}
    assert vendors["cisco_ios"]["supported"] and vendors["juniper_junos"]["supported"]
    assert not vendors["arista_eos"]["supported"] and vendors["cisco_ios"]["parser_version"] == "0.1.0"


# ----------------------------------------------------------------------------- happy paths
def test_upload_cisco_auto_detect(client):
    text = read_sample("cisco_ios_weak.cfg")
    r = upload(client, "edge-sw-01.cfg", text)
    assert r.status_code == 200
    body = r.json()
    assert body["vendor_used"] == "cisco_ios" and body["requested_vendor"] == "auto"
    assert body["file"]["sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert body["result"]["config"]["management"]["telnet_enabled"]["value"] is True
    assert body["detection"]["confidence"] == "high"


@pytest.mark.parametrize("name", ["juniper_junos_weak.set", "juniper_junos_hardened.conf"])
def test_upload_junos_explicit_vendor(client, name):
    r = upload(client, name, read_sample(name), vendor="juniper_junos")
    assert r.status_code == 200 and r.json()["vendor_used"] == "juniper_junos"


def test_response_never_contains_secrets(client):
    blob = upload(client, "a.cfg", read_sample("cisco_ios_weak.cfg")).text
    for secret in ("070C285F4D06", "0822455D0A16", "mERr$hx5rVt7"):
        assert secret not in blob


# ----------------------------------------------------------------------------- invalid input
def test_empty_file(client):
    r = upload(client, "a.cfg", b"")
    assert r.status_code == 400 and error_code(r) == "empty_file"


def test_file_too_large(client, settings):
    settings.max_upload_bytes = 100
    r = upload(client, "a.cfg", b"hostname R1\n" * 50)
    assert r.status_code == 413 and error_code(r) == "file_too_large"


def test_bad_extension_and_binary(client):
    assert upload(client, "run.exe", b"hostname R1").status_code == 415
    r = upload(client, "a.cfg", b"hostname R1\x00\x00")
    assert r.status_code == 415 and error_code(r) == "binary_file"


def test_missing_file_field(client):
    assert client.post("/api/v1/configs/parse", data={"vendor": "auto"}).status_code == 422


def test_unrelated_text_cannot_be_detected(client):
    r = upload(client, "notes.txt", "buy milk\ncall mom\n")
    assert r.status_code == 422 and error_code(r) == "vendor_undetected"


def test_unsupported_vendor_auto_and_explicit(client):
    text = read_sample("arista_eos_unsupported.cfg")
    r = upload(client, "arista.cfg", text)
    assert r.status_code == 422 and error_code(r) == "vendor_unsupported"
    assert "Cisco IOS" in r.json()["error"]["message"]
    r = upload(client, "arista.cfg", text, vendor="arista_eos")
    assert r.status_code == 422 and error_code(r) == "vendor_unsupported"


def test_invalid_vendor_value(client):
    r = upload(client, "a.cfg", read_sample("cisco_ios_weak.cfg"), vendor="nokia")
    assert r.status_code == 422 and error_code(r) == "invalid_vendor"


def test_vendor_mismatch_blocked_and_content_mismatch_not_overridable(client):
    junos = read_sample("juniper_junos_weak.set")
    r = upload(client, "j.set", junos, vendor="cisco_ios")
    assert r.status_code == 422 and error_code(r) == "vendor_mismatch"
    r = upload(client, "j.set", junos, vendor="cisco_ios", force_vendor="true")
    assert r.status_code == 422 and error_code(r) == "vendor_content_mismatch"


def test_explicit_vendor_accepted_when_content_plausible(client):
    # An explicit vendor choice is honoured when the content plausibly matches it.
    text = "hostname R1\nhost-name R1\nline vty 0 4\n transport input ssh\n"
    r = upload(client, "mixed.cfg", text, vendor="cisco_ios")
    assert r.status_code == 200 and r.json()["vendor_used"] == "cisco_ios"


def test_parser_failure_is_reported_without_leaking_content(client, monkeypatch):
    from app.parsers import registry
    secret_marker = "SUPERSECRETMARKER"

    def boom(*_a, **_k):
        raise RuntimeError(secret_marker)

    monkeypatch.setattr(registry.get_parser(registry.Vendor.CISCO_IOS), "parse", boom)
    r = upload(client, "a.cfg", read_sample("cisco_ios_weak.cfg"))
    assert r.status_code == 500 and error_code(r) == "parser_failure"
    assert secret_marker not in r.text


def test_cors_allows_configured_origin_only(client):
    ok = client.options("/api/v1/health", headers={"Origin": "http://localhost:5173",
                                                    "Access-Control-Request-Method": "GET"})
    bad = client.options("/api/v1/health", headers={"Origin": "http://evil.example",
                                                     "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in bad.headers
