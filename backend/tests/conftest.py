import os
import tempfile
from pathlib import Path

# Must be set before the app is imported: the app lifespan (when used) runs against this throw-away database.
_TMP = tempfile.mkdtemp(prefix="netaudit-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/lifespan.db"
os.environ.pop("ADMIN_PASSWORD", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import Settings, get_settings  # noqa: E402
from app.core.ratelimit import reset_rate_limits  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.models import User  # noqa: E402
from app.db.session import get_engine, session_for  # noqa: E402
from app.main import app  # noqa: E402

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
ADMIN = ("admin", "Admin@12345")
VIEWER = ("viewer", "Viewer@12345")


def read_sample(name: str) -> str:
    return (SAMPLES / name).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _reset_limits():
    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture
def settings(tmp_path) -> Settings:
    """Isolated per-test SQLite database, seeded with one admin and one viewer. Rate limiting off by default."""
    s = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path / 'test.db'}", rate_limit_enabled=False,
                 jwt_secret="test-secret-test-secret-test-secret-123456")
    Base.metadata.create_all(get_engine(s.effective_database_url))
    with session_for(s) as db:
        for (name, pw), role in ((ADMIN, "admin"), (VIEWER, "viewer")):
            db.add(User(username=name, password_hash=hash_password(pw), role=role))
        db.commit()
    app.dependency_overrides[get_settings] = lambda: s
    yield s
    app.dependency_overrides.clear()


def login_token(c: TestClient, creds: tuple[str, str]) -> str:
    r = c.post("/api/v1/auth/login", json={"username": creds[0], "password": creds[1]})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def make_client(creds: tuple[str, str] | None) -> TestClient:
    c = TestClient(app)
    if creds:
        c.headers["Authorization"] = f"Bearer {login_token(c, creds)}"
    return c


@pytest.fixture
def anon_client(settings) -> TestClient:
    return make_client(None)


@pytest.fixture
def client(settings) -> TestClient:
    """Authenticated as admin."""
    return make_client(ADMIN)


@pytest.fixture
def viewer_client(settings) -> TestClient:
    return make_client(VIEWER)


def upload(client: TestClient, name: str, data: bytes | str, **form):
    if isinstance(data, str):
        data = data.encode()
    return client.post("/api/v1/configs/parse", files={"file": (name, data, "text/plain")}, data=form)
