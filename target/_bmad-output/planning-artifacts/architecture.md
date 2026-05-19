---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-target-2026-05-18/prd.md
  - src/api/main.py
  - src/api/deps.py
  - src/api/routes/users.py
  - src/api/routes/orders.py
  - src/api/models.py
  - tests/conftest.py
workflowType: architecture
project_name: target
user_name: Luisticas
date: 2026-05-18
---

# Architecture Decision Document
## API Rate Limiting — FastAPI Users-and-Orders Service

---

## 1. Context

The service is a single-process FastAPI application (sync route handlers, uvicorn, SQLite). It has five endpoints across two routers (`/users`, `/orders`) plus a bare `/health` on the app object. There is no existing middleware. Auth is a FastAPI `Depends` on individual route functions (`get_current_user` in `deps.py`). The project prohibits new third-party dependencies without justification (CLAUDE.md).

PRD reference: `_bmad-output/planning-artifacts/prds/prd-target-2026-05-18/prd.md`

---

## 2. Architectural Decisions

### AD-1: No new dependencies — stdlib fixed-window counter

**Decision:** Implement the rate limiter entirely with stdlib (`time`, `threading`, `os`, `collections`). Do not add `slowapi`, `limits`, or any other library.

**Rationale:** The fixed-window algorithm is ~30 lines. The project's CLAUDE.md ("no new third-party dependencies without a clear reason. Stdlib first") is an explicit constraint. `slowapi` adds real value for per-route limit strings and Redis backends, neither of which is in v1 scope. Adding it now creates a dependency whose only job is being a thin wrapper around another dependency (`limits`). Not worth it.

**Trade-off accepted:** Fixed-window counters allow a burst of up to 2× the threshold at a window boundary. This is acceptable for abuse protection at v1 scale; a sliding window can be introduced later without changing the public interface.

---

### AD-2: Router-level dependency, not middleware

**Decision:** Attach the rate limiter as a router-level `dependencies=[Depends(check_rate_limit)]` on both the `users` and `orders` routers. Do not use `app.add_middleware`.

**Rationale:**
- `GET /health` is defined directly on `app` in `main.py`, not on any router. Router-level dependencies naturally exempt it with zero path-matching logic.
- Middleware runs on every request including startup probes, static files, and internal FastAPI machinery. A dependency runs only on matched routes.
- The existing codebase pattern is `Depends`-based (see `get_db`, `get_current_user`). This stays consistent.
- OQ-5 is resolved: middleware exemption via path string matching is fragile; dependency-per-router is precise.

**Wire-up (both routers):**
```python
# users.py
router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(check_rate_limit)])

# orders.py
router = APIRouter(prefix="/orders", tags=["orders"], dependencies=[Depends(check_rate_limit)])
```

---

### AD-3: Unified identity key — X-User-Id if present, else client IP

**Decision:** A single key-extraction function: use `X-User-Id` header value if the header is present in the request; otherwise fall back to `request.client.host`.

**Rationale:** OQ-2 asked whether authenticated endpoints should key on `X-User-Id` and unauthenticated on IP. A simpler equivalent: "use the most specific identity available." If a user header is present, it is more specific than IP (multiple users behind NAT). If absent, fall back to IP. This collapses the two-strategy PRD assumption into one rule with no endpoint-type branching in the limiter.

**Key format:**
- With header: `user:{x_user_id_value}` — prefixed to avoid collision with IP strings
- Without header: `ip:{request.client.host}`

**OQ-2 confirmation:** If `X-User-Id` is absent on an orders endpoint, `get_current_user` raises `401` *after* the rate limiter runs (dependencies resolve in declaration order; router-level runs first). The rate limiter will have keyed on IP and incremented the counter. This is acceptable — an anonymous hammering of the orders endpoint (which will always 401) is still bounded. No special handling needed.

---

### AD-4: Fixed-window algorithm with threading.Lock

**Decision:** Fixed window. Counter dict keyed by client identity, each value `(count, window_start_float)`. Protected by a single `threading.Lock`.

**Why a lock:** FastAPI runs sync route handlers in a thread pool (starlette's `run_in_threadpool`). Multiple threads can access the counter dict concurrently. A `threading.Lock` is the correct primitive.

**Algorithm:**
```
on each request for key K at time now:
  acquire lock
  (count, window_start) = store.get(K, (0, now))
  if now - window_start >= WINDOW_SECONDS:
    count, window_start = 0, now      # new window
  count += 1
  store[K] = (count, window_start)
  release lock
  if count > MAX_REQUESTS:
    retry_after = ceil(WINDOW_SECONDS - (now - window_start))
    raise HTTPException(429, ...)
```

**Memory:** One dict entry per active client identity. Entries for expired windows are not evicted eagerly; they are reset lazily on next access. For a small service this is fine. Restart clears everything.

---

### AD-5: Fail open on unexpected counter error

**Decision:** If the `threading.Lock` acquisition, dict access, or any part of the counter logic raises an unexpected exception, catch it and allow the request through (do not return 500).

**Rationale:** The rate limiter is a safety net, not a business rule. Failing a legitimate request because the counter threw is worse than letting one extra request through. The `HTTPException(429)` is re-raised explicitly after the try/except; it is never swallowed.

---

### AD-6: Configuration via environment variables at module import

**Decision:** Read `RATE_LIMIT_REQUESTS` (default `60`) and `RATE_LIMIT_WINDOW_SECONDS` (default `60`) from `os.environ` at module import time in `rate_limit.py`. No dynamic reloading.

**Rationale:** Matches the service's existing config style (DATABASE_URL is a module-level constant in `deps.py`). Operators change limits by setting env vars and restarting — consistent with FR-5.

---

## 3. Files Changed

### New file: `src/api/rate_limit.py`

Complete implementation. Contains:
- Module-level constants `MAX_REQUESTS` and `WINDOW_SECONDS` from env vars
- `_store: dict[str, tuple[int, float]]` — the counter
- `_lock: threading.Lock`
- `_get_key(request: Request) -> str` — identity extraction
- `check_rate_limit(request: Request) -> None` — the FastAPI dependency

```python
import os
import threading
import time

from fastapi import Depends, HTTPException, Request

MAX_REQUESTS: int = int(os.environ.get("RATE_LIMIT_REQUESTS", "60"))
WINDOW_SECONDS: float = float(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))

_store: dict[str, tuple[int, float]] = {}
_lock = threading.Lock()


def _get_key(request: Request) -> str:
    user_id = request.headers.get("x-user-id")
    if user_id:
        return f"user:{user_id}"
    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"


def check_rate_limit(request: Request) -> None:
    key = _get_key(request)
    now = time.time()
    limited = False
    retry_after = int(WINDOW_SECONDS) + 1
    try:
        with _lock:
            count, window_start = _store.get(key, (0, now))
            if now - window_start >= WINDOW_SECONDS:
                count, window_start = 0, now
            count += 1
            _store[key] = (count, window_start)
            if count > MAX_REQUESTS:
                limited = True
                retry_after = max(1, int(WINDOW_SECONDS - (now - window_start)) + 1)
    except Exception:
        return  # fail open
    if limited:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
```

---

### Modified: `src/api/routes/users.py`

Change only the `APIRouter` instantiation line:

```python
# before
router = APIRouter(prefix="/users", tags=["users"])

# after
from fastapi import APIRouter, Depends, HTTPException
from api.rate_limit import check_rate_limit

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(check_rate_limit)])
```

No changes to any route function.

---

### Modified: `src/api/routes/orders.py`

Change only the `APIRouter` instantiation line:

```python
# before
router = APIRouter(prefix="/orders", tags=["orders"])

# after
from api.rate_limit import check_rate_limit

router = APIRouter(prefix="/orders", tags=["orders"], dependencies=[Depends(check_rate_limit)])
```

No changes to any route function.

---

### No changes: `src/api/main.py`, `src/api/deps.py`, `src/api/models.py`, `pyproject.toml`

`/health` remains on `app` directly and is never touched by the rate limiter.

---

### New file: `tests/test_rate_limit.py`

Uses the existing `client` fixture from `conftest.py`. The key challenge: `MAX_REQUESTS` and `WINDOW_SECONDS` are module-level constants read at import time, so tests must either:
- Use `monkeypatch.setenv` + `importlib.reload(rate_limit)`, or
- Directly patch `rate_limit.MAX_REQUESTS` and reset `rate_limit._store`

**Decision: Patch the module-level constants and reset `_store` between tests.** This is simpler than reloading and avoids import-order problems.

Test cases to implement:

| Test | What it asserts |
|---|---|
| `test_requests_within_limit_pass` | N requests ≤ MAX_REQUESTS all return non-429 |
| `test_request_over_limit_returns_429` | Request N+1 returns 429 |
| `test_429_has_retry_after_header` | 429 response has `Retry-After` header with positive int |
| `test_429_body_has_detail_field` | 429 JSON body has `detail` key |
| `test_health_endpoint_exempt` | 10× limit requests to `/health` all return 200 |
| `test_window_reset_allows_new_requests` | After patching window_start to past, next request passes |
| `test_different_identities_tracked_separately` | Two different X-User-Id values each get their own counter |
| `test_env_var_override` | Patching `MAX_REQUESTS=2` enforces limit of 2 |

Test setup pattern:
```python
import pytest
import api.rate_limit as rl

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    original_max = rl.MAX_REQUESTS
    original_window = rl.WINDOW_SECONDS
    rl._store.clear()
    rl.MAX_REQUESTS = 3  # low limit for fast tests
    yield
    rl._store.clear()
    rl.MAX_REQUESTS = original_max
    rl.WINDOW_SECONDS = original_window
```

---

## 4. Open Questions Resolution

| OQ | Resolution |
|---|---|
| OQ-1 | `/health` exempt via router-level dependency (not on any router). Single threshold for all routed endpoints. |
| OQ-2 | Unified key: `X-User-Id` if present, else IP. Rate limiter fires before `get_current_user` on orders; unauthenticated order attempts still consume a counter slot (keyed on IP). Acceptable. |
| OQ-3 | Default 60 req/min stands. No known batch jobs — operator can override via env var. |
| OQ-4 | Fail open. Implemented via try/except in `check_rate_limit`. |
| OQ-5 | Router-level `Depends`, not middleware. |
| OQ-6 | Stdlib only. No new dependencies. |

---

## 5. What Does NOT Change

- No schema/migration needed — rate limiter has no DB state
- No auth logic changes — `get_current_user` is untouched
- No changes to existing test fixtures — `client` fixture in `conftest.py` works as-is
- `_store` must be cleared between tests (handled by `reset_rate_limiter` fixture above)

---

## 6. Story Handoff Summary

One story is sufficient:

**Story: Add in-memory rate limiting to the API**

- Create `src/api/rate_limit.py` with `check_rate_limit` dependency (see §3 for full implementation)
- Wire `dependencies=[Depends(check_rate_limit)]` into both router instantiations
- Create `tests/test_rate_limit.py` covering all 8 test cases in §3
- Verify `GET /health` is unaffected; `pytest` passes

Acceptance criteria map directly to FR-1 through FR-5 in the PRD.
