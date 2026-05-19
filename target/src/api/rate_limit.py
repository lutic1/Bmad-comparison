import os
import threading
import time
from typing import Callable

from fastapi import Header, HTTPException, Request

DEFAULT_LIMIT = int(os.environ.get("RATE_LIMIT_REQUESTS", "60"))
DEFAULT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))

# Counters live in-process; multi-worker deployments get N×limit effective cap.
_counters: dict[str, tuple[int, float]] = {}
_lock = threading.Lock()

# Swappable for tests.
_now: Callable[[], float] = time.monotonic


def reset() -> None:
    with _lock:
        _counters.clear()


def _check(key: str, limit: int, window: int) -> None:
    now = _now()
    with _lock:
        count, window_start = _counters.get(key, (0, now))
        if now - window_start >= window:
            count = 0
            window_start = now
        count += 1
        _counters[key] = (count, window_start)
        if count > limit:
            retry_after = max(1, int(window - (now - window_start)))
            raise HTTPException(
                status_code=429,
                detail="rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )


def rate_limit_ip(limit: int, window: int):
    def dep(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        _check(f"ip:{ip}:{request.url.path}", limit, window)

    return dep


def rate_limit_user(limit: int, window: int):
    def dep(
        request: Request,
        x_user_id: int | None = Header(default=None),
    ) -> None:
        if x_user_id is not None:
            key = f"user:{x_user_id}:{request.url.path}"
        else:
            ip = request.client.host if request.client else "unknown"
            key = f"ip:{ip}:{request.url.path}"
        _check(key, limit, window)

    return dep
