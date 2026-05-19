import os
import threading
import time
from math import ceil

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

EXEMPT_PATHS = {"/health"}


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._counters: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            count, window_start = self._counters.get(key, (0, now))
            if now - window_start >= self.window_seconds:
                count = 0
                window_start = now
            if count >= self.max_requests:
                retry_after = max(1, ceil(self.window_seconds - (now - window_start)))
                return False, retry_after
            self._counters[key] = (count + 1, window_start)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


limiter = RateLimiter(
    max_requests=_env_int("RATE_LIMIT_MAX", 60),
    window_seconds=_env_int("RATE_LIMIT_WINDOW", 60),
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        user_id = request.headers.get("x-user-id")
        if user_id:
            key = f"user:{user_id}"
        elif request.client is not None:
            key = f"ip:{request.client.host}"
        else:
            key = "ip:unknown"

        allowed, retry_after = limiter.check(key)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)
