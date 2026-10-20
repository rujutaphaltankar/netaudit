"""Database engine / session handling (SQLite by default, PostgreSQL via DATABASE_URL)."""
from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings


@lru_cache
def get_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def _enable_fk(dbapi_conn, _):  # SQLite needs foreign keys switched on for ON DELETE CASCADE
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
        return engine
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 3} if url.startswith("postgresql") else {})


@lru_cache
def _sessionmaker(url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(url), autoflush=False, expire_on_commit=False)


def get_db(settings: Settings = Depends(get_settings)) -> Iterator[Session]:
    db = _sessionmaker(settings.effective_database_url)()
    try:
        yield db
    finally:
        db.close()


def session_for(settings: Settings) -> Session:
    return _sessionmaker(settings.effective_database_url)()


def check_database(url: str) -> str:
    try:
        with get_engine(url).connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "unavailable"
