# Add rate limiting to the API

## Context

The FastAPI service currently has no protection against request flooding —
any client can hit `/users`, `/orders`, etc. as fast as they want. The task
is to add basic rate limiting so abusive clients are throttled with HTTP
`429 Too Many Requests`.

Constraints from `CLAUDE.md`:

- **Stdlib first** — "No new third-party dependencies without a clear reason."
  So no `slowapi` / `fastapi-limiter`. A custom in-memory limiter is
  appropriate for this single-process SQLite service.
- **Small, focused change** — don't refactor unrelated code, don't add
  speculative features.
- **Tests required** — "Every change ships with tests."
- **Don't add logging / metrics / middleware unless the task asks for it.**
  Rate limiting *is* the task, so middleware is in scope.

## Approach

Sliding-window in-memory limiter, keyed on client IP, wired as a single
FastAPI HTTP middleware. `GET /health` is exempt so liveness probes never
get throttled. On rejection: HTTP 429 with `Retry-After` header and a
`{"detail": "rate limit exceeded"}` body — matching the project's existing
`HTTPException` error shape.

Limit is configurable via env var `RATE_LIMIT_PER_MINUTE` (default 60).
This is one knob, not a config surface — just enough so tests can dial it
down without monkey-patching internals.

## Files

### New: `src/api/rate_limit.py`

Owns the limiter. Roughly:

```python
import os
import threading
import time
from collections import deque


class SlidingWindowLimiter:
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> tuple[bool, float]:
        """Return (allowed, retry_after_seconds)."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= self.max_requests:
                retry_after = q[0] + self.window_seconds - now
                return False, max(retry_after, 0.0)
            q.append(now)
            return True, 0.0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def _build_default_limiter() -> SlidingWindowLimiter:
    per_minute = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60"))
    return SlidingWindowLimiter(max_requests=per_minute, window_seconds=60.0)


limiter = _build_default_limiter()
```

Module-level singleton `limiter` so the middleware and tests share state.

### Modified: `src/api/main.py`

Add a single `@app.middleware("http")` function that:

1. Skips `/health` (early `return await call_next(request)`).
2. Computes a key: `request.client.host if request.client else "anonymous"`.
3. Calls `limiter.check(key)`. If denied, returns
   `JSONResponse(status_code=429, content={"detail": "rate limit exceeded"},
    headers={"Retry-After": str(max(1, int(retry_after) + 1))})`.
4. Otherwise proxies to `call_next`.

Imports: `from fastapi import Request`, `from fastapi.responses import
JSONResponse`, `from api.rate_limit import limiter`.

### New: `tests/test_rate_limit.py`

Cover the four behaviours that matter:

1. **Under the limit, requests succeed** — using a small limit, fire N
   requests, all return 200 (or their natural status).
2. **At the limit, the next request returns 429 with `Retry-After`** —
   fire `max_requests + 1`, assert last response is 429 and has
   `Retry-After` header.
3. **`/health` is exempt** — burst /health far beyond the limit, all 200.
4. **Different keys are isolated** — two distinct `request.client.host`
   values don't share a budget. Easiest way: directly unit-test
   `SlidingWindowLimiter.check("a")` vs `check("b")` rather than fight
   `TestClient`'s fixed client address.

Tests use the existing `client` fixture. To make 429 testable without
firing 60+ requests, the test temporarily lowers the limit by replacing
the module-level limiter's internals (or constructs its own
`SlidingWindowLimiter` for the unit tests in #4).

Concrete pattern for #2:

```python
def test_returns_429_when_limit_exceeded(client, monkeypatch):
    from api import rate_limit
    monkeypatch.setattr(rate_limit.limiter, "max_requests", 3)
    rate_limit.limiter.reset()

    for _ in range(3):
        r = client.get("/users/1")
        assert r.status_code in (200, 404)  # 404 is fine — user not created

    r = client.get("/users/1")
    assert r.status_code == 429
    assert r.json() == {"detail": "rate limit exceeded"}
    assert "Retry-After" in r.headers
```

### Modified: `tests/conftest.py`

Add an autouse fixture that resets the limiter before each test, so test
order doesn't matter:

```python
@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    from api.rate_limit import limiter
    limiter.reset()
    yield
```

Place it after the existing fixtures. No other changes to `conftest.py`.

## Verification

Run from repo root:

```
pytest -q
```

All existing tests must still pass (the default 60/min limit is far above
what any single test triggers). New tests in `tests/test_rate_limit.py`
must pass.

Manual smoke (optional):

```
uvicorn api.main:app
# in another shell, burst /users/1 with a tight loop and confirm 429
RATE_LIMIT_PER_MINUTE=5 uvicorn api.main:app
```

## Out of scope

- Distributed / Redis-backed limiting (single-process service).
- Per-endpoint or per-method limits — one global limit is enough for now.
- Logging or metrics on rate-limit events (CLAUDE.md: don't add logging
  unless asked).
- Whitelisting or admin bypass.
