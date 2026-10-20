"""Small in-memory sliding-window rate limiter (per process). Adequate for a single-instance deployment;
use a shared store (e.g. Redis) or a reverse proxy limit when scaling horizontally."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.core.errors import AppError

_BUCKETS: dict[tuple[str, str], deque[float]] = defaultdict(deque)


def reset_rate_limits() -> None:
    _BUCKETS.clear()


def rate_limit(name: str, max_calls: int, window_seconds: int, key: Callable[[Request], str] | None = None):
    def dependency(request: Request, settings: Settings = Depends(get_settings)) -> None:
        if not settings.rate_limit_enabled:
            return
        ident = key(request) if key else (request.client.host if request.client else "unknown")
        bucket = _BUCKETS[(name, ident)]
        now = time.monotonic()
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()
        if len(bucket) >= max_calls:
            retry = max(1, int(window_seconds - (now - bucket[0])))
            raise AppError(429, "rate_limited", f"Too many requests. Try again in {retry} seconds.", {"retry_after": retry})
        bucket.append(now)
    return dependency
