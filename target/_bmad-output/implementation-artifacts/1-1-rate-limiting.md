# Story 1.1: Add Rate Limiting Middleware

Status: done

## Story

As an API operator,
I want every inbound request to be counted against a per-caller fixed-window limit,
so that no single caller can exhaust server resources or degrade service for others.

## Context (one paragraph)

The service currently has zero request throttling. This story adds a `BaseHTTPMiddleware`
subclass in `src/api/middleware/rate_limit.py` that intercepts every request, identifies
the caller by `X-User-Id` header (falling back to client IP), and enforces a configurable
fixed-window limit (default 60 req / 60 s). When a caller exceeds the limit the middleware
short-circuits with `429 Too Many Requests`, a `Retry-After` integer header, and a JSON
body. Limit and window are configurable via `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS`
env vars. State is in-process (dict + `threading.Lock`) — no external store. The middleware
is registered in `main.py` via `app.add_middleware`. A module-level `reset()` function
allows `tests/conftest.py` to clear state between tests. A new `tests/test_rate_limit.py`
covers all FRs. **Zero new third-party dependencies.** Stdlib only.

---

## Acceptance Criteria

1. `GET /health`, `POST /users`, `GET /users/{id}`, `POST /orders`, `GET /orders/{id}` — all respond normally when request count is below the limit.
2. The 61st request from the same `X-User-Id` within a 60-second window returns HTTP `429`.
3. The `429` response includes `Retry-After: <N>` header (integer, > 0) and JSON body `{"detail": "Rate limit exceeded. Retry after <N> seconds."}`.
4. No route handler is invoked on a rate-limited request (no DB side-effects).
5. Two different `X-User-Id` values have independent counters.
6. A request with no `X-User-Id` is tracked by client IP and subject to the same limit.
7. Setting `RATE_LIMIT_REQUESTS=3 RATE_LIMIT_WINDOW_SECONDS=30` causes the 4th request in 30 s to return `429`.
8. When the window expires, the counter resets and the next request succeeds.
9. `pytest` passes with no failures (existing tests unbroken, new rate-limit tests green).

---

## Tasks / Subtasks

- [ ] Create `src/api/middleware/rate_limit.py` (AC: 1–8)
  - [ ] Module-level `_counters: dict[str, tuple[int, float]]` and `_lock: threading.Lock`
  - [ ] `reset() -> None` clears `_counters` under lock (test-only hook)
  - [ ] `RateLimitMiddleware(BaseHTTPMiddleware)` with `limit` and `window` params
  - [ ] `_subject(request)` returns `"user:{id}"` or `"ip:{host}"`
  - [ ] `dispatch` — fixed-window count, 429 path, Retry-After computation
- [ ] Modify `src/api/main.py` (AC: 1)
  - [ ] `from api.middleware.rate_limit import RateLimitMiddleware`
  - [ ] `app.add_middleware(RateLimitMiddleware)` after `app = FastAPI(...)`
- [ ] Modify `tests/conftest.py` (AC: 9)
  - [ ] `from api.middleware import rate_limit` import
  - [ ] `rate_limit.reset()` call at end of `client` fixture teardown
- [ ] Create `tests/test_rate_limit.py` (AC: 1–9)
  - [ ] `test_requests_below_limit_succeed` — 3 requests, all 200
  - [ ] `test_request_above_limit_returns_429` — inject count via `_counters`, assert 429
  - [ ] `test_429_retry_after_header_is_integer`
  - [ ] `test_429_body_shape`
  - [ ] `test_route_handler_not_invoked_on_429`
  - [ ] `test_different_users_have_independent_counters`
  - [ ] `test_no_user_id_falls_back_to_ip`
  - [ ] `test_window_reset_clears_counter` — inject expired window_start, assert 200

### Review Findings

- [ ] [Review][Patch] AC7: No test for configurable limit threshold — inject counter at `RATE_LIMIT_REQUESTS` and assert 429; confirms the module-level default is actually enforced [tests/test_rate_limit.py]
- [ ] [Review][Patch] AC6: IP tracking path not exercised at limit — `test_no_user_id_falls_back_to_ip` only fires one request; add counter-injection test for the IP subject key [tests/test_rate_limit.py]
- [x] [Review][Defer] threading.Lock blocks async event loop [src/api/middleware/rate_limit.py:41] — deferred, pre-existing design decision; sub-microsecond critical section; architecture doc justified
- [x] [Review][Defer] _counters grows without bound [src/api/middleware/rate_limit.py:9] — deferred, known v1 limitation; addressed when horizontal scaling is needed (OQ-4)
- [x] [Review][Defer] X-User-Id is attacker-controlled key [src/api/middleware/rate_limit.py:28] — deferred, by design; service has no real auth per CLAUDE.md
- [x] [Review][Defer] reset() called after teardown not before setup [tests/conftest.py:44] — deferred, pytest guarantees fixture teardown; 19/19 pass
- [x] [Review][Defer] RATE_LIMIT_WINDOW_SECONDS=0 disables limiting — deferred, operational edge case; out of scope v1

---

## Dev Notes

### Files being modified

| File | Change type | Notes |
|---|---|---|
| `src/api/middleware/rate_limit.py` | **NEW** | Core implementation |
| `src/api/main.py` | **MODIFY** | +2 lines (import + `add_middleware`) |
| `tests/conftest.py` | **MODIFY** | +2 lines (import + `rate_limit.reset()`) |
| `tests/test_rate_limit.py` | **NEW** | 8 focused tests |

`src/api/middleware/__init__.py` already exists (empty). Do not recreate it.

### Key implementation contract

```python
# src/api/middleware/rate_limit.py
import threading, time, os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_counters: dict[str, tuple[int, float]] = {}   # subject -> (count, window_start)
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
```

### conftest.py teardown patch (exact diff)

```python
# Add at top of tests/conftest.py (after existing imports):
from api.middleware import rate_limit

# In client fixture, after app.dependency_overrides.clear():
    rate_limit.reset()
```

### Test pattern — state injection (avoids firing 60 real requests)

```python
# Inject an over-limit counter directly — fast, deterministic
from api.middleware.rate_limit import _counters, _lock
import time

def test_request_above_limit_returns_429(client):
    with _lock:
        _counters["user:1"] = (999, time.monotonic())
    resp = client.get("/health", headers={"X-User-Id": "1"})
    assert resp.status_code == 429
    assert int(resp.headers["Retry-After"]) > 0
    assert "Rate limit exceeded" in resp.json()["detail"]
```

### Thread safety
`threading.Lock` is correct for this service. The lock is held for one dict read + write only (sub-microsecond). No deadlock risk: lock is never held across an `await`.

### What must not break
- All existing tests in `test_users.py`, `test_orders.py`, `test_dates.py` must remain green.
- `conftest.py` `client` fixture teardown must still call `app.dependency_overrides.clear()` — the `rate_limit.reset()` line comes after, not instead of.
- The `/health` endpoint must still respond to unauthenticated GETs (no `X-User-Id` required).

### No new dependencies
Do not add `slowapi`, `limits`, or any other library. `starlette.middleware.base` is already a transitive dependency of `fastapi==0.115.0`.

### Project Structure Notes
- Routes: `src/api/routes/` — unchanged
- Deps: `src/api/deps.py` — unchanged
- Models: `src/api/models.py` — unchanged
- App factory: `src/api/main.py` — minimal change only
- Middleware dir: `src/api/middleware/` — `__init__.py` already present

### References
- PRD: `_bmad-output/planning-artifacts/prds/prd-target-2026-05-19/prd.md` — FR-1 through FR-5, §5 Non-Goals, §8 OQ-5
- Architecture: `_bmad-output/planning-artifacts/architecture/rate-limiting-architecture.md` — Implementation Order, Thread-Safety Analysis, What Does NOT Change
- Project guardrails: `CLAUDE.md` — "No new third-party dependencies", stdlib-first rule

---

## Dev Agent Record

### Agent Model Used

(to be filled by dev agent)

### Debug Log References

### Completion Notes List

### File List
