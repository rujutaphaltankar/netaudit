from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, select

from app.core.config import Settings
from app.db.base import Base
from app.db.models import Audit, User
from app.db.session import get_engine, session_for
from app.services import bootstrap


def test_migrations_create_exactly_the_model_schema(tmp_path):
    s = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path / 'm.db'}")
    bootstrap.run_migrations(s)
    engine = get_engine(s.effective_database_url)
    assert {"users", "audits", "findings", "ai_mappings"} <= set(inspect(engine).get_table_names())
    with engine.connect() as conn:
        assert compare_metadata(MigrationContext.configure(conn), Base.metadata) == []  # no drift
    bootstrap.run_migrations(s)  # re-running is safe


def test_startup_seeds_admin_and_demo_data_idempotently(tmp_path):
    s = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path / 's.db'}", seed_demo_data=True, admin_password="Another!Pass123")
    bootstrap.startup(s)
    bootstrap.startup(s)
    with session_for(s) as db:
        assert {u.username: u.role for u in db.scalars(select(User))} == {"admin": "admin", "viewer": "viewer"}
        audits = db.scalars(select(Audit).order_by(Audit.created_at)).all()
        assert len(audits) == 4 and audits[0].created_at < audits[-1].created_at
        assert {a.grade for a in audits} == {"F", "A"}


def test_startup_without_demo_data_creates_only_admin(tmp_path):
    s = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path / 'n.db'}")
    bootstrap.startup(s)
    with session_for(s) as db:
        assert [u.username for u in db.scalars(select(User))] == ["admin"]
        assert db.scalars(select(Audit)).first() is None


def test_app_lifespan_runs_startup():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        assert c.get("/api/v1/health").json()["database"] == "ok"
