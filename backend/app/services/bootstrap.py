"""Startup tasks: settings validation, migrations, first admin, optional demo data."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password
from app.db.models import Audit, User
from app.db.session import session_for
from app.rules.engine import evaluate_config
from app.services.audit_service import persist_audit
from app.services.config_pipeline import analyze_config
from app.services.upload_validation import validate_upload

log = logging.getLogger("netaudit.bootstrap")
BACKEND_DIR = Path(__file__).resolve().parents[2]
DEV_ADMIN_PASSWORD = "Admin@12345"
DEV_VIEWER_PASSWORD = "Viewer@12345"
DEFAULT_SECRET_PREFIX = "dev-insecure-secret"

# (sample file, days ago): spread over time so the dashboard trend chart is meaningful.
DEMO_AUDITS = [("cisco_ios_weak.cfg", 21), ("juniper_junos_weak.set", 14),
               ("cisco_ios_hardened.cfg", 7), ("juniper_junos_hardened.conf", 2)]


def validate_settings(settings: Settings) -> None:
    if not settings.is_production:
        return
    problems = []
    if settings.jwt_secret.startswith(DEFAULT_SECRET_PREFIX) or len(settings.jwt_secret) < 32:
        problems.append("JWT_SECRET must be set to a random value of at least 32 characters")
    if not settings.admin_password or len(settings.admin_password) < 12:
        problems.append("ADMIN_PASSWORD must be set and at least 12 characters")
    if settings.admin_password in (DEV_ADMIN_PASSWORD, "ChangeMe!ChangeMe1"):
        problems.append("ADMIN_PASSWORD must not be a documented default")
    if problems:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))


def run_migrations(settings: Settings) -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", settings.effective_database_url.replace("%", "%%"))
    command.upgrade(cfg, "head")


def ensure_user(db: Session, username: str, password: str, role: str) -> User:
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        user = User(username=username, password_hash=hash_password(password), role=role)
        db.add(user)
        db.commit()
        log.info("created_user username=%s role=%s", username, role)
    return user


def find_samples_dir(settings: Settings) -> Path | None:
    candidates = [settings.samples_dir, BACKEND_DIR.parent / "samples", BACKEND_DIR / "samples"]
    return next((Path(c) for c in candidates if c and Path(c).is_dir()), None)


def seed_demo(db: Session, settings: Settings, admin: User) -> int:
    if db.scalar(select(func.count()).select_from(Audit)):
        return 0
    samples = find_samples_dir(settings)
    if samples is None:
        log.warning("demo_seed_skipped reason=samples_dir_not_found")
        return 0
    created = 0
    for name, days_ago in DEMO_AUDITS:
        path = samples / name
        if not path.is_file():
            continue
        upload = validate_upload(name, path.read_bytes(), settings)
        parsed = analyze_config(upload, "auto", False)
        persist_audit(db, admin, parsed, evaluate_config(parsed.result.config),
                      created_at=datetime.now(timezone.utc) - timedelta(days=days_ago))
        created += 1
    log.info("demo_seed audits=%d", created)
    return created


def startup(settings: Settings) -> None:
    validate_settings(settings)
    if settings.auto_migrate:
        run_migrations(settings)
    with session_for(settings) as db:
        if not settings.admin_password:
            log.warning("ADMIN_PASSWORD not set: using the documented development password. Never do this in production.")
        admin = ensure_user(db, settings.admin_username, settings.admin_password or DEV_ADMIN_PASSWORD, "admin")
        if settings.seed_demo_data:
            ensure_user(db, "viewer", DEV_VIEWER_PASSWORD, "viewer")
            seed_demo(db, settings, admin)
