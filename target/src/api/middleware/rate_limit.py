import math
import os
import threading
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

RATE_LIMIT_REQUESTS: int = int(os.environ.get("RATE_LIMIT_REQUESTS", "60"))
RATE_LIMIT_WINDOW_SECONDS: int = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))


class RateLimitStore:
    def __init__(self, limit: int = RATE_LIMIT_REQUESTS, window: int = RATE_LIMIT_WINDOW_SECONDS) -> None:
        self._limit = limit
        self._window = window
        self._store: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def check_and_increment(self, key: str) -> tuple[bool, int, float]:
        now = time.time()
        with self._lock:
            count, window_start = self._store.get(key, (0, now))
            if now - window_start >= self._window:
                count = 0
                window_start = now
            window_reset_ts = window_start + self._window
            if count >= self._limit:
                return False, 0, window_reset_ts
            count += 1
            self._store[key] = (count, window_start)
            return True, self._limit - count, window_reset_ts


_store = RateLimitStore()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, store: RateLimitStore | None = None) -> None:
        super().__init__(app)
        self._store = store if store is not None else _store

    async def dispatch(self, request: Request, call_next):
        user_id = request.headers.get("x-user-id")
        if user_id is not None:
            key = user_id
        else:
            client = request.client
            host = client.host if client else "unknown"
            key = f"ip:{host}"

        allowed, remaining, reset_ts = self._store.check_and_increment(key)

        headers = {
            "X-RateLimit-Limit": str(self._store._limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(reset_ts)),
        }

        if not allowed:
            retry_after = math.ceil(reset_ts - time.time())
            headers["Retry-After"] = str(max(retry_after, 1))
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers=headers,
            )

        response = await call_next(request)
        for name, value in headers.items():
            response.headers[name] = value
        return response
