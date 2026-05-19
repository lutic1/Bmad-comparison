# Add Rate Limiting to the API

## Context

The API has no request throttling. Any client can hammer endpoints without bound. This adds per-IP rate limiting (60 req/min) as a Starlette middleware — stdlib only, no new dependencies.

## Approach

**Algorithm:** Sliding window using `collections.deque` of timestamps per IP. On each request, evict entries older than 60 s, reject if ≥ 60 remain, otherwise append current timestamp and proceed. Sliding window prevents burst exploitation across fixed-window boundaries.

**Storage:** Module-level `dict[str, deque[float]]` in the new middleware module. Safe without locks — asyncio is single-threaded and no `await` occurs between the check and the append.

**Client IP:** `request.client.host` (Starlette populates from ASGI scope). Fall back to `"unknown"` if `request.client` is `None`.

## Files to Change

### 1. Create `src/api/middleware.py` (new)

```python
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
```

### 2. Edit `src/api/main.py`

Add after existing imports:
```python
from api.middleware import RateLimitMiddleware
```

Add after `app = FastAPI(...)`:
```python
app.add_middleware(RateLimitMiddleware)
```

`add_middleware` must be called before `include_router` calls (it wraps the entire app stack at startup).

### 3. Create `tests/test_rate_limit.py` (new)

```python
import time
from collections import deque

import pytest

from api.middleware import RATE_LIMIT, WINDOW_SECONDS, _buckets


@pytest.fixture
def rate_limit_client(client):
    _buckets.clear()
    yield client
    _buckets.clear()


def _fill_bucket(ip: str = "testclient", age: float = 0.0) -> None:
    now = time.time()
    _buckets[ip] = deque(now - age for _ in range(RATE_LIMIT))


def test_requests_below_limit_succeed(rate_limit_client):
    for _ in range(RATE_LIMIT - 1):
        assert rate_limit_client.get("/health").status_code == 200


def test_60th_request_succeeds(rate_limit_client):
    for _ in range(RATE_LIMIT):
        resp = rate_limit_client.get("/health")
    assert resp.status_code == 200


def test_61st_request_returns_429(rate_limit_client):
    _fill_bucket()
    assert rate_limit_client.get("/health").status_code == 429


def test_429_response_body(rate_limit_client):
    _fill_bucket()
    assert rate_limit_client.get("/health").text == "Too Many Requests"


def test_window_expiry_allows_new_requests(rate_limit_client):
    _fill_bucket(age=WINDOW_SECONDS + 1)
    assert rate_limit_client.get("/health").status_code == 200


def test_rate_limit_applies_to_all_routes(rate_limit_client):
    _fill_bucket()
    assert rate_limit_client.get("/users/1").status_code == 429


def test_different_ips_are_independent(rate_limit_client):
    _fill_bucket(ip="192.168.1.1")
    assert rate_limit_client.get("/health").status_code == 200
```

Tests avoid `time.sleep` by directly manipulating `_buckets`. The `rate_limit_client` fixture clears buckets before/after each test for isolation. Existing tests are unaffected — they send ≪ 60 requests total.

## Verification

```bash
# All existing tests still pass
pytest tests/test_users.py tests/test_orders.py tests/test_dates.py -v

# New rate limit tests pass
pytest tests/test_rate_limit.py -v

# Manual smoke test (optional)
uvicorn api.main:app --reload
for i in $(seq 1 62); do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health; done
# Expect: 60 lines of "200", then "429"
```
