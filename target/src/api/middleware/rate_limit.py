from time import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

RATE_LIMIT = 100
WINDOW_SECONDS = 60.0


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, limit: int = RATE_LIMIT,
                 window: float = WINDOW_SECONDS,
                 store: dict | None = None) -> None:
        super().__init__(app)
        self._limit = limit
        self._window = window
        self._store: dict[str, tuple[int, float]] = {} if store is None else store

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path == "/health":
            return await call_next(request)

        ip: str = request.client.host if request.client else "unknown"
        now: float = time()
        count, window_start = self._store.get(ip, (0, now))

        if now - window_start >= self._window:
            count, window_start = 0, now

        count += 1
        self._store[ip] = (count, window_start)

        if count > self._limit:
            return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)

        return await call_next(request)
