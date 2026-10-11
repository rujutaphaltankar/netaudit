"""Database connectivity. Models and migrations arrive in Phase 6; for now only a health check."""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


@lru_cache
def get_engine(url: str) -> Engine:
    connect_args = {"connect_timeout": 3} if url.startswith("postgresql") else {}
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


def check_database(url: str | None) -> str:
    if not url:
        return "not_configured"
    try:
        with get_engine(url).connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "unavailable"
