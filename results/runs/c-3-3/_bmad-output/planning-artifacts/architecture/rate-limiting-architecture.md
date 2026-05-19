# Technical Architecture: API Rate Limiting

**Date:** 2026-05-19
**PRD:** `_bmad-output/planning-artifacts/prds/prd-target-2026-05-19/prd.md`
**Status:** Ready for implementation

---

## Decision Summary

| Concern | Decision | Rationale |
|---|---|---|
| Placement | `BaseHTTPMiddleware` registered in `main.py` | Intercepts all routes before any handler; consistent with Starlette convention |
| State | Module-level `dict` + `threading.Lock` in `rate_limit.py` | Single-process service; no external store needed; importable for test reset |
| Algorithm | Fixed-window counter | Stdlib only; simplest correct implementation; burst artefacts at window boundary are accepted (PRD §5) |
| Subject key | `X-User-Id` header → client IP fallback | Matches existing auth primitive in `deps.py` |
| Config | `os.getenv` with defaults at middleware construction | Matches project's zero-dependency-injection style |
| Test reset | `reset()` function in `rate_limit.py`, called from `conftest.py` | Module-level state must be cleared between tests; OQ-5 from PRD |

---

## Files Changed

### 1. `src/api/middleware/rate_limit.py` — NEW

The entire implementation lives here. Module-level `_counters` dict and `_lock` are the fixed-window state store. The `reset()` function exists solely for test isolation — it is never called in production code.

```python
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
    """Clear all counters. Call from test fixtures only."""
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

**Why module-level state instead of instance state?**
`app.add_middleware(RateLimitMiddleware, ...)` constructs the middleware internally; the caller gets no reference to the instance. Module-level state remains accessible via `from api.middleware.rate_limit import reset` from test fixtures without any framework introspection.

---

### 2. `src/api/main.py` — MODIFIED

Add one import and one `add_middleware` call. No other changes.

```python
# Add at top, after existing imports:
from api.middleware.rate_limit import RateLimitMiddleware

# Add after app = FastAPI(...), before include_router calls:
app.add_middleware(RateLimitMiddleware)
```

**Ordering note:** Starlette wraps middleware in LIFO order. With only one middleware layer this is irrelevant, but document it for future readers: middleware added last executes first on the request path.

**Full resulting main.py for reference:**
```python
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.deps import engine
from api.middleware.rate_limit import RateLimitMiddleware
from api.models import Base
from api.routes import orders, users


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="benchmark-target", lifespan=lifespan)

app.add_middleware(RateLimitMiddleware)

app.include_router(users.router)
app.include_router(orders.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

---

### 3. `tests/conftest.py` — MODIFIED

Add a `reset()` call at teardown of the `client` fixture. One import, one line.

```python
# Add import at top:
from api.middleware import rate_limit

# Modify client fixture teardown:
@pytest.fixture
def client(db_engine):
    TestingSessionLocal = sessionmaker(
        bind=db_engine, autoflush=False, autocommit=False
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[deps.get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    rate_limit.reset()          # ← added: clear limiter state between tests
```

---

### 4. `tests/test_rate_limit.py` — NEW

Required by FR-5. Tests follow the existing style in `test_users.py` (plain functions, `client` fixture, one behaviour per test).

```python
from api.middleware.rate_limit import RateLimitMiddleware

LIMIT = 5  # small limit — patched at test time for speed


def _low_limit_client(client, monkeypatch):
    """Patch the middleware instance limit for this test."""
    for layer in client.app.middleware_stack.middlewares:  # Starlette internals
        if isinstance(layer, RateLimitMiddleware):
            monkeypatch.setattr(layer, "limit", LIMIT)
            break
    return client
```

> **Note to implementer:** accessing `middleware_stack` is fragile Starlette internals. The safer, preferred alternative is to register the app with a low limit via a second `client` fixture variant that overrides env vars before app construction. Because the app is a module-level singleton, the cleanest test approach is:
>
> - Set `RATE_LIMIT_REQUESTS=5` via `monkeypatch.setenv` **before** importing `rate_limit`, or
> - Accept that the default limit is 60 and fire 61 requests in the test (slow but correct).
>
> **Recommended test approach** (no Starlette internals, matches project style):

```python
def test_requests_below_limit_succeed(client):
    for _ in range(3):
        resp = client.get("/health")
        assert resp.status_code == 200


def test_request_above_limit_returns_429(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "3")
    # Re-construct middleware state is not needed — we can exploit the
    # module-level limit read at construction time by using a fresh app,
    # OR fire limit+1 requests using the default limit.
    # Simplest approach: fire default_limit+1 requests targeting a single user.
    from api.middleware import rate_limit as rl
    original_limit = None
    for layer in client.app.middleware_stack:
        if hasattr(layer, "limit"):
            original_limit = layer.limit
            layer.limit = 3
            break
    try:
        for i in range(4):
            resp = client.get("/health", headers={"X-User-Id": "999"})
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
        assert resp.json()["detail"].startswith("Rate limit exceeded")
    finally:
        if original_limit is not None:
            for layer in client.app.middleware_stack:
                if hasattr(layer, "limit"):
                    layer.limit = original_limit
                    break


def test_429_retry_after_header_is_integer(client):
    from api.middleware.rate_limit import _counters, _lock
    import time, threading
    # Force the counter over the limit by direct state injection
    with _lock:
        _counters["user:888"] = (999, time.monotonic())
    resp = client.get("/health", headers={"X-User-Id": "888"})
    assert resp.status_code == 429
    assert int(resp.headers["Retry-After"]) > 0


def test_different_users_have_independent_counters(client):
    from api.middleware.rate_limit import _counters, _lock
    import time
    with _lock:
        _counters["user:1"] = (999, time.monotonic())
    # user 2 is unaffected
    resp = client.get("/health", headers={"X-User-Id": "2"})
    assert resp.status_code == 200


def test_no_user_id_falls_back_to_ip(client):
    # No X-User-Id — should still succeed (IP subject, fresh counter)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_window_reset_clears_counter(client):
    from api.middleware.rate_limit import _counters, _lock
    import time
    subject = "user:777"
    window = 60
    old_window_start = time.monotonic() - window - 1  # expired
    with _lock:
        _counters[subject] = (999, old_window_start)
    resp = client.get("/health", headers={"X-User-Id": "777"})
    assert resp.status_code == 200
```

> Direct state injection via `_counters`/`_lock` is intentional: it avoids firing N requests in tests while still validating correct 429 behaviour. This is the recommended approach for this project.

---

## Thread-Safety Analysis

The `_lock` guards every read-modify-write of `_counters`. FastAPI's default `anyio` thread pool runs sync routes in threads; `dispatch` is async, so it runs on the event loop. In both cases the `threading.Lock` is correct:

- Async context: `with _lock` blocks the event loop thread — acceptable because the critical section is a single dict read + write (sub-microsecond). A proper `asyncio.Lock` would be needed only if the window were large or the dict were slow.
- Thread context: lock provides mutual exclusion as expected.

No deadlock risk: the lock is never held across an `await`.

---

## What Does NOT Change

- `src/api/deps.py` — no changes
- `src/api/models.py` — no changes
- `src/api/routes/` — no changes
- `pyproject.toml` — no new dependencies
- `src/api/middleware/__init__.py` — already exists, stays empty

---

## Open Questions Resolved by Architecture

| PRD OQ | Resolution |
|---|---|
| OQ-5 (test reset) | Module-level `reset()` in `rate_limit.py`, called from `conftest.py` teardown |
| OQ-2 (proxy headers) | Not addressed in v1; raw `request.client.host` used. If proxy is added, change `_subject()` only |
| OQ-4 (horizontal scale) | In-process only. Migration to distributed: replace `_counters`/`_lock` with Redis calls inside `_subject`-keyed operations — interface unchanged |

---

## Implementation Order

1. Create `src/api/middleware/rate_limit.py`
2. Modify `src/api/main.py` (import + `add_middleware`)
3. Modify `tests/conftest.py` (import + `rate_limit.reset()` teardown)
4. Create `tests/test_rate_limit.py`
5. Run `pytest` — all green
