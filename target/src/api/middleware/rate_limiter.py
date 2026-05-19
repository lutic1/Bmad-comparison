import threading
import time
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp


class RateLimitError(BaseModel):
    detail: str
    retry_after: int


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, limit: int = 100, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.limit = limit
        self.window_seconds = window_seconds
        self._counters: dict[tuple[str, int], int] = {}
        self._lock = threading.Lock()

    def _get_scope(self, request: Request) -> str:
        user_id = request.headers.get("X-User-Id")
        if user_id:
            return f"user:{user_id}"
        host = request.client.host if request.client else "unknown"
        return f"ip:{host}"

    def _get_window_start(self) -> int:
        return int(time.time() // self.window_seconds) * self.window_seconds

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        now = time.time()
        window_start = self._get_window_start()
        scope = self._get_scope(request)
        reset_ts = window_start + self.window_seconds
        retry_after = max(1, int(reset_ts - now))

        with self._lock:
            key = (scope, window_start)
            count = self._counters.get(key, 0) + 1
            self._counters[key] = count

        remaining = max(0, self.limit - count)

        if count > self.limit:
            error = RateLimitError(detail="Rate limit exceeded", retry_after=retry_after)
            return JSONResponse(
                content=error.model_dump(),
                status_code=429,
                headers={
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_ts),
                    "Retry-After": str(retry_after),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_ts)
        return response
