import time
from collections import deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

RATE_LIMIT = 60
WINDOW_SECONDS = 60

_buckets: dict[str, deque[float]] = {}


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        bucket = _buckets.setdefault(ip, deque())
        while bucket and now - bucket[0] > WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT:
            return Response("Too Many Requests", status_code=429)
        bucket.append(now)
        return await call_next(request)
