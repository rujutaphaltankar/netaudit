from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app

SAMPLES = Path(__file__).resolve().parents[2] / "samples"


def read_sample(name: str) -> str:
    return (SAMPLES / name).read_text(encoding="utf-8")


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None)


@pytest.fixture
def client(settings: Settings):
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def upload(client: TestClient, name: str, data: bytes | str, **form):
    if isinstance(data, str):
        data = data.encode()
    return client.post("/api/v1/configs/parse", files={"file": (name, data, "text/plain")}, data=form)
