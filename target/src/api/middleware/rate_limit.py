import os
import threading
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_counters: dict[str, tuple[int, float]] = {}
_lock = threading.Lock()

RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))


def reset() -> None:
    with _lock:
        _counters.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int = RATE_LIMIT_REQUESTS, window: int = RATE_LIMIT_WINDOW_SECONDS):
        super().__init__(app)
        self.limit = limit
        self.window = window

    def _subject(self, request: Request) -> str:
        user_id = request.headers.get("x-user-id")
        if user_id:
            return f"user:{user_id}"
        host = request.client.host if request.client else "unknown"
        return f"ip:{host}"

    async def dispatch(self, request: Request, call_next):
        subject = self._subject(request)
        now = time.monotonic()
        retry_after = None

        with _lock:
            stored_count, window_start = _counters.get(subject, (0, now))
            if now - window_start >= self.window:
                stored_count, window_start = 0, now
            new_count = stored_count + 1
            _counters[subject] = (new_count, window_start)
            if new_count > self.limit:
                retry_after = int(window_start + self.window - now) + 1

        if retry_after is not None:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Retry after {retry_after} seconds."},
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)
