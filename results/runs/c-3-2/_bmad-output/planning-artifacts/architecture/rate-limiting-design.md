# Architecture Design: API Rate Limiting

**Date:** 2026-05-19
**PRD:** `_bmad-output/planning-artifacts/prds/prd-target-2026-05-19/prd.md`
**Status:** Final

---

## 1. Codebase Snapshot

| Layer | Files |
|---|---|
| App entry | `src/api/main.py` |
| Dependencies | `src/api/deps.py` — `get_db`, `get_current_user` |
| Models | `src/api/models.py` — User, Order, OrderItem |
| Routes | `src/api/routes/users.py`, `src/api/routes/orders.py` |
| Tests | `tests/conftest.py` (client + db_engine fixtures), `tests/test_users.py`, `tests/test_orders.py` |
| Runtime | Single-process FastAPI/Uvicorn, SQLite, no external cache |
| Dependencies | No Redis, no external rate-limit library. Stdlib only. |

---

## 2. Key Decisions

### D1: FastAPI dependency, not Starlette middleware

**Chosen:** A `Depends(check_rate_limit)` added to the two routers.

**Why not middleware:**
- Middleware runs before routing; it has no access to parsed path params or the
  dependency injection graph. Raising `HTTPException` from middleware requires
  manual JSON serialisation.
- The existing pattern is `Depends(get_db)` / `Depends(get_current_user)`. A
  dependency matches that pattern exactly.

**Why not app-level `dependencies=[...]`:**
- `app = FastAPI(dependencies=[Depends(check_rate_limit)])` would also rate-limit
  `/health`, which should be exempt so load-balancer health probes don't consume quota.
- Per-router injection (`app.include_router(..., dependencies=[...])`) is the
  surgical option.

### D2: Sliding-window counter (deque of timestamps)

**Chosen:** `collections.defaultdict(collections.deque)` — maps `client_key → deque[float]` of accepted request timestamps.

On each request:
1. Prune timestamps older than `now - window_seconds`.
2. If `len(deque) >= limit` → raise 429, `Retry-After = ceil(oldest + window - now)`.
3. Else append `now`, let request through.

**Why sliding over fixed window:**
- Fixed window allows a 2× burst at the window boundary (last request in window N,
  first request in window N+1). Sliding window eliminates that attack surface.
- Complexity cost is identical; stdlib `deque` is O(1) append/popleft.

**Thread safety:** CPython's GIL serialises dict lookups and deque popleft/append
in a single-process Uvicorn deployment. No explicit lock needed for the v1
single-worker assumption. If multi-worker is adopted, replace the in-process store
with a Redis sorted-set counter.

### D3: Client key = X-User-Id header, fallback to request.client.host

`POST /users` does not require auth, so `X-User-Id` may be absent. Fallback to
source IP covers that case without breaking the unauthenticated endpoint.

### D4: Configuration via environment variables

| Variable | Default | Meaning |
|---|---|---|
| `RATE_LIMIT_REQUESTS` | `100` | Max requests per window per client |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Window duration in seconds |

Read at module import. Restart required to apply changes — acceptable per PRD §6.2.

---

## 3. Files That Change

### New: `src/api/rate_limit.py`

```python
import os
import time
from collections import defaultdict, deque
from math import ceil

from fastapi import Depends, Header, HTTPException, Request

_LIMIT = int(os.environ.get("RATE_LIMIT_REQUESTS", "100"))
_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))

_store: dict[str, deque] = defaultdict(deque)


def check_rate_limit(
    request: Request,
    x_user_id: int | None = Header(default=None),
) -> None:
    key = str(x_user_id) if x_user_id is not None else (request.client.host if request.client else "unknown")
    now = time.monotonic()
    window = _store[key]

    # prune expired
    while window and window[0] <= now - _WINDOW:
        window.popleft()

    if len(window) >= _LIMIT:
        retry_after = ceil(window[0] + _WINDOW - now)
        raise HTTPException(
            status_code=429,
            detail="rate limit exceeded",
            headers={"Retry-After": str(max(1, retry_after))},
        )

    window.append(now)
```

> **Note:** `_store` is module-level — it persists across requests in the same
> process. Each test run gets an isolated process via `TestClient`, so no
> cross-test leakage in the existing fixture design. If needed, tests can
> clear `_store` directly or monkeypatch the limit to a low value.

### Modified: `src/api/main.py`

Add `Depends(check_rate_limit)` to both router registrations. `/health` is
registered directly on `app` and is unaffected.

```python
from api.rate_limit import check_rate_limit

app.include_router(users.router, dependencies=[Depends(check_rate_limit)])
app.include_router(orders.router, dependencies=[Depends(check_rate_limit)])
```

### New: `tests/test_rate_limit.py`

Tests use the existing `client` fixture. They monkeypatch `rate_limit._LIMIT` to
a small value (e.g. 3) to avoid making 100 requests per assertion.

Key scenarios:
1. Requests up to limit succeed (200/201).
2. Request at limit+1 → 429 with `detail: "rate limit exceeded"`.
3. 429 response includes `Retry-After` header (integer ≥ 1).
4. Different `X-User-Id` values have independent counters.
5. No `X-User-Id` (unauthenticated to `/users`) — IP-keyed counter enforced.
6. `/health` is not rate-limited (survives limit+N requests).

---

## 4. Files That Do NOT Change

| File | Reason |
|---|---|
| `src/api/deps.py` | Rate limiting is independent of DB/auth deps |
| `src/api/models.py` | No schema changes; counters are in-memory |
| `src/api/routes/users.py` | No route-level changes needed |
| `src/api/routes/orders.py` | No route-level changes needed |
| `pyproject.toml` | No new dependencies; stdlib only |
| `tests/conftest.py` | Existing fixtures are sufficient |

---

## 5. Open Questions Resolved for Architecture

| OQ | Resolution |
|---|---|
| OQ-2: Which endpoints? | All `/users` and `/orders` routes; `/health` exempt |
| OQ-3: Client key | `X-User-Id` if present, else source IP |
| OQ-5: Multi-worker? | Assumed single-process for v1; in-memory is sufficient |
| OQ-6: Config mechanism | Environment variables |
| OQ-7: Latency budget | Sliding window over a deque is O(n) prune + O(1) append; negligible overhead at 100 req/window |

**Still open (PM to resolve before ship):**
- OQ-1: Why now / urgency (does not block implementation)
- OQ-4: Agreed default limits — current default (100/60s) is an assumption; confirm with PM

---

## 6. Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Multi-worker deployment invalidates in-memory counters | Low (single-process assumed) | Document; v2 path is Redis sorted-set |
| `request.client` is None behind some proxies | Low | Fallback to `"unknown"` key (all proxy-hidden clients share one bucket) — acceptable for v1 |
| Tests leak state between runs via module-level `_store` | Low | `TestClient` uses a fresh event loop per test; monkeypatching `_LIMIT` to a small value keeps tests fast and independent |
