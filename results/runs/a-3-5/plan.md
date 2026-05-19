# Add rate limiting to the API

## Context

The FastAPI service in `src/api/` has no rate limiting today: any client
can hammer `POST /users`, `GET /users/{id}`, or the order endpoints as
fast as they like. We want a simple cap so a single user or IP can't
flood the service. The repo's guardrails are explicit ("no new
third-party deps without a clear reason", "stdlib first", "don't add
middleware unless the task asks for it"), so the design uses stdlib only
and reaches for FastAPI's existing `Depends()` mechanism rather than
middleware that intercepts everything.

## Approach

A small in-memory **fixed-window** limiter, exposed as FastAPI
dependencies and applied per-route. Public routes are keyed by client
IP, authenticated routes by `X-User-Id`. `/health` is unaffected.

### Why fixed-window in-memory
- Single process (uvicorn + SQLite). No need for Redis or a shared
  store.
- Fixed-window is ~30 lines of stdlib code; no third-party dep needed.
- Sliding window / token bucket are nicer in theory but overkill for
  this service.
- Trade-off: if the operator ever runs multiple workers, each worker has
  its own counter (effective limit = N × workers). Documented inline.

## Files to add / change

### New: `src/api/rate_limit.py`
A self-contained module with:
- A module-level `dict[str, tuple[int, float]]` mapping
  `key → (count, window_start_epoch)`. Protected by `threading.Lock`
  (FastAPI runs sync endpoints in a threadpool).
- `_check(key, limit, window)` — increments the counter for `key`. If
  the window has elapsed, resets. If `count > limit`, raises
  `HTTPException(status_code=429, headers={"Retry-After": str(...)})`.
- Two dependency factories:
  - `rate_limit_ip(limit: int, window: int)` — returns a dependency that
    reads `request.client.host` (via `Request` from `fastapi`) and calls
    `_check(f"ip:{ip}:{route}", limit, window)`. Keyed per route so a
    burst on `POST /users` doesn't eat the budget for `GET /users/{id}`.
  - `rate_limit_user(limit: int, window: int)` — same shape but keys on
    the `X-User-Id` header. Falls back to IP if the header is missing
    (defence in depth; the auth dependency will reject the request
    anyway).
- A `reset()` helper for tests to clear the in-memory state between
  cases.
- Limit/window values default to **60 requests per 60 seconds**,
  overridable via env vars `RATE_LIMIT_REQUESTS` and
  `RATE_LIMIT_WINDOW_SECONDS` read once at import time using `os.environ`
  (stdlib).

### Modify: `src/api/routes/users.py`
Add the IP-keyed dependency to both routes:
```python
from api.rate_limit import rate_limit_ip, DEFAULT_LIMIT, DEFAULT_WINDOW

@router.post("", ..., dependencies=[Depends(rate_limit_ip(DEFAULT_LIMIT, DEFAULT_WINDOW))])
def create_user(...): ...

@router.get("/{user_id}", ..., dependencies=[Depends(rate_limit_ip(DEFAULT_LIMIT, DEFAULT_WINDOW))])
def get_user(...): ...
```

### Modify: `src/api/routes/orders.py`
Add the user-keyed dependency to both routes (same shape, swap
`rate_limit_user` for `rate_limit_ip`). Order: place the limiter
dependency **before** `get_current_user` so an over-limit request is
rejected with 429 without doing a DB lookup.

### Untouched
- `src/api/main.py` — no middleware needed, `/health` stays unlimited.
- `src/api/deps.py` — rate-limit code lives in its own module so
  `deps.py` stays focused on DB/auth.
- `pyproject.toml` — no new dependencies.

## Tests

Add `tests/test_rate_limit.py`. Use the existing `client` fixture from
`tests/conftest.py`. Call `rate_limit.reset()` in an autouse fixture so
state doesn't leak between tests.

Cover:
1. **Under limit** — N requests where N == limit all return 2xx.
2. **Over limit, public route** — limit+1 requests to `GET /users/{id}`
   from the same client return 429 on the last one, with a `Retry-After`
   header.
3. **Over limit, authed route** — same as above for `POST /orders` with
   a fixed `X-User-Id`. Verify a *different* `X-User-Id` is not blocked
   (per-user keying works).
4. **Window resets** — monkeypatch `time.monotonic` (or the time source
   used inside `rate_limit.py`) to fast-forward past the window and
   confirm a follow-up request succeeds. This avoids `time.sleep()` in
   tests.
5. **`/health` is exempt** — many requests in a row all return 200.

For test ergonomics, expose the time source as a module-level
`_now = time.monotonic` so tests can swap it via monkeypatch.

## Verification

1. `pytest -q` — full suite green, including the new `test_rate_limit.py`.
2. Manual smoke:
   ```
   uvicorn api.main:app --reload
   for i in $(seq 1 65); do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/users/1; done
   ```
   Expect the first 60 to be 404 (no user) and the last 5 to be 429.
3. Confirm `/health` is unaffected:
   `for i in $(seq 1 200); do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health; done`
   — all 200.
4. Confirm env-var override works:
   `RATE_LIMIT_REQUESTS=3 RATE_LIMIT_WINDOW_SECONDS=60 uvicorn ...` then
   observe 429 on the 4th request.

## Out of scope

- Distributed/multi-worker correctness (would need Redis or similar —
  the repo doesn't run multi-worker today).
- Per-route custom limits beyond the single default (easy follow-up:
  the dependency factories already take `limit`/`window` args).
- Rate-limit response body shape beyond FastAPI's default
  `{"detail": "..."}` and the `Retry-After` header.
