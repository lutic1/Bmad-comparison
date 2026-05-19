# Plan: Add Rate Limiting to the API

## Context

The API has no rate limiting. Any client can hammer endpoints indefinitely. This adds per-IP fixed-window rate limiting via Starlette middleware using only stdlib — no new dependencies.

## Approach

**Algorithm:** Fixed-window counter per client IP. Each IP gets a counter that resets every 60 seconds. Requests beyond the limit within that window get HTTP 429.

**Defaults:** 100 requests / 60 seconds. The `/health` endpoint is excluded.

**Test isolation:** The middleware accepts an optional `store: dict` constructor param. Tests inject a fresh dict and a low limit (3) via a minimal FastAPI app, completely isolated from the production `app` singleton.

**Existing tests:** Not affected. TestClient uses `request.client.host = "testclient"`. Existing tests make ~17 requests total, well under the 100-request limit.

---

## Files

### Create: `src/api/middleware/__init__.py`
Empty file — makes the directory a Python package.

### Create: `src/api/middleware/rate_limit.py`

```python
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
```

### Modify: `src/api/main.py`

Add import and wire up middleware (after existing router includes):

```python
from api.middleware.rate_limit import RateLimitMiddleware
# ...
app.add_middleware(RateLimitMiddleware)
```

### Create: `tests/test_rate_limit.py`

Five tests using an isolated test app (limit=3, fresh store):

1. `test_requests_under_limit_succeed` — 3 requests → all 200
2. `test_request_exceeding_limit_returns_429` — 4th request → 429
3. `test_429_body_is_json` — verify `{"detail": "Rate limit exceeded"}`
4. `test_health_endpoint_skipped` — exhaust limit, then `/health` still 200
5. `test_window_reset_allows_requests_again` — backdate store timestamp > 60s, confirm counter resets to 200

---

## Verification

```bash
cd /Users/luisticas/bmad-demo/target
pytest tests/test_rate_limit.py -v   # new tests pass
pytest tests/test_users.py tests/test_orders.py -v  # existing tests unaffected
```
