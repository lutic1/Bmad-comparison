# Add rate limiting to the API

## Context

The FastAPI service in this repo currently has no protection against abusive
clients — any caller can hammer `/users`, `/orders`, etc. without bound. We
want a basic rate limit that returns `429 Too Many Requests` when a client
exceeds an allowed request rate.

Constraints from `CLAUDE.md`:

- **"No new third-party dependencies without a clear reason. Stdlib first."**
  → rules out `slowapi` / `limits` / `redis`. A small in-process implementation
  is more than enough for this single-process SQLite service.
- **"Don't add logging, metrics, tracing, or middleware unless the task asks
  for it."** → the task explicitly asks for rate limiting, which is naturally
  expressed as middleware. That's allowed; we will not add anything else
  (no metrics, no logging) along the way.
- **"Every change ships with tests."** → we must add pytest coverage.

## Approach

A single in-process, fixed-window counter, applied as an ASGI middleware in
`main.py`. No new dependencies.

- **Key**: `X-User-Id` header when present, otherwise `request.client.host`.
  This mirrors how `get_current_user` already treats the header as identity.
- **Algorithm**: Fixed window of `WINDOW_SECONDS` (default 60s) with a max of
  `MAX_REQUESTS` (default 60) per key. Stored in a plain `dict[str, tuple[int, float]]`
  guarded by a `threading.Lock` (TestClient and uvicorn workers can both
  call into it from threads).
- **Configuration**: Read `RATE_LIMIT_MAX` and `RATE_LIMIT_WINDOW` from
  environment variables at module import, with defaults `60` and `60`. This
  matters for tests — they need a small limit to trigger 429 quickly.
- **Response shape on exceed**: `429` with JSON body `{"detail": "rate limit exceeded"}`
  and a `Retry-After` header (seconds remaining in the window).
- **Exemption**: `/health` is exempt so liveness checks aren't throttled.

## Files to change

### New: `src/api/middleware/__init__.py`
Empty package marker (the directory already exists).

### New: `src/api/middleware/rate_limit.py`
- Define `RateLimiter` class with `check(key: str) -> tuple[bool, int]` returning
  `(allowed, retry_after_seconds)`. Uses `time.monotonic()` and a `threading.Lock`.
- Define `RateLimitMiddleware` (a `BaseHTTPMiddleware` subclass) that:
  - Reads `RATE_LIMIT_MAX` / `RATE_LIMIT_WINDOW` from env at construction.
  - Skips `request.url.path == "/health"`.
  - Picks the key: `request.headers.get("x-user-id") or (request.client.host if request.client else "unknown")`.
  - Calls `limiter.check(key)`; on deny returns `JSONResponse(status_code=429, ...)` with `Retry-After`.
  - On allow, awaits `call_next(request)`.
- Expose a module-level `limiter` instance so tests can reset its state between cases.

### Modified: `src/api/main.py`
Add `app.add_middleware(RateLimitMiddleware)` after the routers are included
(order doesn't matter for ASGI middleware registration, but keep it grouped
with app setup). Import from `api.middleware.rate_limit`.

### Modified: `tests/conftest.py`
Add a `reset_rate_limiter` autouse fixture (or call it inside the existing
`client` fixture) that clears the limiter's internal dict before each test.
Without this, the 60-req default would leak counts across tests and make the
existing `test_users` / `test_orders` flaky once enough tests run.

### New: `tests/test_rate_limit.py`
Cover at minimum:
1. **Under the limit**: first N requests to `/users` (POST) all succeed (201).
2. **Over the limit**: the (N+1)th request returns 429 with `Retry-After` header set.
3. **Per-key isolation**: two different `X-User-Id` headers each get their own budget.
4. **Health exemption**: `/health` can be called many times without ever returning 429.
5. **Window reset**: after monkey-patching `time.monotonic` (or directly resetting
   the limiter) the limit refills.

Use `monkeypatch.setenv("RATE_LIMIT_MAX", "3")` + re-import or, simpler, mutate
`limiter.max_requests` directly for tests to keep the request counts small and
the tests fast.

## Existing utilities reused

- `request.client.host` (FastAPI/Starlette built-in) for the IP fallback.
- The existing `X-User-Id` header convention from `api/deps.py:get_current_user`
  — same header, same semantics.
- The existing `client` fixture in `tests/conftest.py` — no need for a separate
  HTTP client.

## What we are explicitly NOT doing

- No `slowapi`, `limits`, or `redis` dependency.
- No sliding-window or token-bucket — fixed window is the simplest correct thing.
- No per-route override decorators — one global policy.
- No logging of rate-limit events (CLAUDE.md: "don't add logging … unless asked").
- No distributed/multi-process support. The current service is single-process
  SQLite; if it ever scales out, the limiter would need an external store, but
  that's out of scope.

## Verification

1. `pytest` — all existing tests still pass, new `test_rate_limit.py` passes.
2. Manual smoke (optional): `uvicorn api.main:app` and
   `for i in $(seq 1 70); do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/users/1; done`
   — should show a run of 200/404s followed by 429s.
3. Confirm `/health` is never throttled: `for i in $(seq 1 200); do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health; done` returns 200s only.
