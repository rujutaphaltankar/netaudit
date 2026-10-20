import pytest

from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.db.session import session_for
from app.services.bootstrap import validate_settings
from app.core.config import Settings
from tests.conftest import ADMIN, VIEWER, make_client, upload, read_sample

API = "/api/v1"


def test_password_hashing_roundtrip():
    h = hash_password("S3cret!pass")
    assert "S3cret" not in h and h.startswith("scrypt$")
    assert verify_password("S3cret!pass", h) and not verify_password("wrong", h)
    assert not verify_password("x", "garbage")


def test_login_success_and_me(anon_client):
    r = anon_client.post(f"{API}/auth/login", json={"username": "ADMIN", "password": ADMIN[1]})  # case-insensitive username
    assert r.status_code == 200 and r.json()["user"]["role"] == "admin" and "password" not in r.text
    me = anon_client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.json()["username"] == "admin"


def test_login_failures_are_indistinguishable(anon_client):
    a = anon_client.post(f"{API}/auth/login", json={"username": "admin", "password": "nope"})
    b = anon_client.post(f"{API}/auth/login", json={"username": "ghost", "password": "nope"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


def test_protected_endpoints_require_a_valid_token(anon_client, settings):
    for path in ("/audits", "/audits/stats", "/rules", "/auth/me", "/users", "/ai-mappings"):
        assert anon_client.get(API + path).status_code == 401, path
    assert upload(anon_client, "a.cfg", read_sample("cisco_ios_weak.cfg")).status_code == 401
    bad = anon_client.get(f"{API}/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert bad.status_code == 401 and bad.json()["error"]["code"] == "invalid_token"
    expired = create_access_token(1, "admin", settings.jwt_secret, -1)
    assert anon_client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    forged = create_access_token(1, "admin", "another-secret-another-secret-123456", 5)
    assert anon_client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_viewer_is_read_only(viewer_client):
    assert viewer_client.get(f"{API}/audits").status_code == 200
    assert viewer_client.get(f"{API}/rules").status_code == 200
    files = {"file": ("a.cfg", read_sample("cisco_ios_weak.cfg").encode(), "text/plain")}
    assert viewer_client.post(f"{API}/audits", files=files).status_code == 403
    assert viewer_client.get(f"{API}/users").status_code == 403
    assert viewer_client.delete(f"{API}/audits/1").status_code == 403


def test_admin_manages_users(client, settings):
    r = client.post(f"{API}/users", json={"username": "alice", "password": "alicepass1", "role": "viewer"})
    assert r.status_code == 201 and r.json()["role"] == "viewer"
    assert client.post(f"{API}/users", json={"username": "ALICE", "password": "alicepass1"}).status_code == 409
    assert client.post(f"{API}/users", json={"username": "bob", "password": "short"}).status_code == 422
    assert client.post(f"{API}/users", json={"username": "b b", "password": "longenough1"}).status_code == 422
    uid = r.json()["id"]
    assert client.patch(f"{API}/users/{uid}", json={"is_active": False}).json()["is_active"] is False
    login = make_client(None).post(f"{API}/auth/login", json={"username": "alice", "password": "alicepass1"})
    assert login.status_code == 401  # deactivated
    me = client.get(f"{API}/auth/me").json()["id"]
    assert client.patch(f"{API}/users/{me}", json={"role": "viewer"}).status_code == 400  # cannot demote self
    assert client.patch(f"{API}/users/9999", json={"is_active": True}).status_code == 404


def test_deactivated_user_token_stops_working(client, settings):
    token_client = make_client(VIEWER)
    with session_for(settings) as db:
        u = db.query(User).filter_by(username="viewer").one()
        u.is_active = False
        db.commit()
    assert token_client.get(f"{API}/auth/me").status_code == 401


def test_login_is_rate_limited(settings):
    settings.rate_limit_enabled = True
    c = make_client(None)
    codes = [c.post(f"{API}/auth/login", json={"username": "admin", "password": "bad"}).status_code for _ in range(12)]
    assert codes[:10] == [401] * 10 and codes[10] == 429


def test_production_settings_are_validated():
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        validate_settings(Settings(_env_file=None, environment="production", admin_password="a-long-admin-password"))
    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
        validate_settings(Settings(_env_file=None, environment="production", jwt_secret="x" * 40))
    validate_settings(Settings(_env_file=None, environment="production", jwt_secret="x" * 40, admin_password="a-long-admin-password"))
    validate_settings(Settings(_env_file=None, environment="development"))  # dev defaults are allowed
