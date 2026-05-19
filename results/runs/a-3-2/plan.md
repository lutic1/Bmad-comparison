# Plan: Add Rate Limiting to the API

## Context
The API has no rate limiting. Any client can make unlimited requests, which risks resource exhaustion. The task is to add per-identity rate limiting: requests are counted per `X-User-Id` (or client IP for anonymous endpoints) within a fixed time window, returning HTTP 429 when exceeded.

## Approach

**Mechanism:** A FastAPI dependency (`rate_limit`) added globally to the app. This follows the existing dependency injection pattern (`get_current_user`), avoids middleware (per CLAUDE.md), and allows easy override in tests via `app.dependency_overrides`.

**Algorithm:** Fixed window counter — track `(count, window_start)` per key; reset when the window expires. Stdlib only (`time`, `threading`).

**Key:** `X-User-Id` header if present, else `request.client.host`. Distinct identities get independent buckets.

**Limit:** 60 requests per 60-second window (configurable via module-level constants for test patching).

---

## Files to Create / Modify

### 1. Create `src/api/rate_limit.py`

```python
import threading
import time

from fastapi import HTTPException, Request

WINDOW = 60   # seconds
LIMIT = 60    # requests per window

_lock = threading.Lock()
_counters: dict[str, tuple[int, float]] = {}


def rate_limit(request: Request) -> None:
    key = request.headers.get("x-user-id") or (
        request.client.host if request.client else "unknown"
    )
    now = time.monotonic()
    with _lock:
        count, window_start = _counters.get(key, (0, now))
        if now - window_start >= WINDOW:
            count, window_start = 0, now
        if count >= LIMIT:
            retry_after = int(WINDOW - (now - window_start))
            raise HTTPException(
                status_code=429,
                detail="rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )
        _counters[key] = (count + 1, window_start)
```

### 2. Modify `src/api/main.py`

Add global dependency so all routes are covered without touching individual handlers:

```python
from fastapi import Depends, FastAPI
from api.rate_limit import rate_limit

app = FastAPI(title="benchmark-target", lifespan=lifespan, dependencies=[Depends(rate_limit)])
```

### 3. Create `tests/test_rate_limit.py`

Tests use monkeypatching to set `LIMIT = 2` and clear `_counters` so we don't need 61 real requests:

- `test_requests_within_limit_succeed` — 2 requests, both 2xx
- `test_request_exceeding_limit_returns_429` — 3rd request → 429 with `Retry-After` header
- `test_different_users_have_independent_limits` — user A exhausted, user B still succeeds
- `test_anonymous_requests_are_rate_limited` — no `X-User-Id`, IP-keyed bucket still enforced

Fixture pattern:
```python
@pytest.fixture(autouse=True)
def patch_rate_limit(monkeypatch):
    import api.rate_limit as rl
    monkeypatch.setattr(rl, "LIMIT", 2)
    rl._counters.clear()
    yield
    rl._counters.clear()
```

---

## Verification

```bash
pytest tests/test_rate_limit.py -v   # new tests pass
pytest                                # full suite still passes
```
