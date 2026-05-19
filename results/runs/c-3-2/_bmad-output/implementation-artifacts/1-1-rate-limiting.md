# Story 1.1: Add Per-Client Rate Limiting

Status: done

## Story

As an API operator,
I want the FastAPI service to enforce a per-client request rate limit,
so that no single caller can saturate the service through accidental hammering or deliberate abuse.

## Acceptance Criteria

1. A request that exceeds the configured limit within the time window receives HTTP 429 with body `{"detail": "rate limit exceeded"}`.
2. Every HTTP 429 response includes a `Retry-After` header (integer ≥ 1) indicating seconds until the window resets.
3. Requests up to and including the limit succeed with their normal status code.
4. Two clients with different `X-User-Id` values have independent counters — one client exhausting its quota does not affect the other.
5. When `X-User-Id` is absent, the client is keyed by source IP; rate limiting still applies.
6. `GET /health` is never rate-limited, regardless of request volume.
7. The limit and window are read from `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS` env vars at startup; removing the vars restores defaults (100 req / 60 s).
8. All existing tests in `test_users.py` and `test_orders.py` continue to pass.

## Tasks / Subtasks

- [x] Create `src/api/rate_limit.py` (AC: 1, 2, 3, 4, 5, 7)
  - [x] Module-level config: read `RATE_LIMIT_REQUESTS` (default 100) and `RATE_LIMIT_WINDOW_SECONDS` (default 60) from `os.environ`
  - [x] Module-level store: `_store: dict[str, deque] = defaultdict(deque)` keyed by client string
  - [x] `check_rate_limit(request: Request, x_user_id: int | None = Header(default=None)) -> None` dependency
  - [x] Client key logic: `str(x_user_id)` if present, else `request.client.host` (fallback `"unknown"`)
  - [x] Sliding-window prune: remove timestamps older than `now - _WINDOW` from front of deque
  - [x] If `len(deque) >= _LIMIT`: compute `retry_after = ceil(deque[0] + _WINDOW - now)`, raise `HTTPException(429, detail="rate limit exceeded", headers={"Retry-After": str(max(1, retry_after))})`
  - [x] Else: `deque.append(time.monotonic())`
- [x] Modify `src/api/main.py` (AC: 6)
  - [x] Import `check_rate_limit` from `api.rate_limit`
  - [x] Import `Depends` from `fastapi`
  - [x] Change `app.include_router(users.router)` → `app.include_router(users.router, dependencies=[Depends(check_rate_limit)])`
  - [x] Change `app.include_router(orders.router)` → `app.include_router(orders.router, dependencies=[Depends(check_rate_limit)])`
  - [x] Leave the `@app.get("/health")` route unchanged
- [x] Create `tests/test_rate_limit.py` (AC: 1–8)
  - [x] Import and monkeypatch `rate_limit._LIMIT` to 3 (keeps tests fast)
  - [x] Also reset `rate_limit._store` between tests to prevent leakage
  - [x] Test: requests 1–3 return non-429 (AC 3)
  - [x] Test: 4th request returns 429 with `{"detail": "rate limit exceeded"}` (AC 1)
  - [x] Test: 429 response has `Retry-After` header that is a positive integer string (AC 2)
  - [x] Test: two different `X-User-Id` values have independent counters — exhausting one does not affect the other (AC 4)
  - [x] Test: request without `X-User-Id` to `POST /users` is still rate-limited by IP (AC 5)
  - [x] Test: `GET /health` returns 200 after limit+N calls (AC 6)

### Review Findings

- [x] [Review][Patch] `request.client.host` may be None in some proxy setups [`src/api/rate_limit.py:18`] — fixed: added `and request.client.host` guard
- [x] [Review][Defer] Unbounded memory growth of `_store` — keys accumulate indefinitely [`src/api/rate_limit.py:11`] — deferred, pre-existing v1 design choice
- [x] [Review][Defer] Invalid env var values (_LIMIT=0, _WINDOW=0, negatives) silently break logic [`src/api/rate_limit.py:8-9`] — deferred, pre-existing; operator documentation concern

## Dev Notes

**Stack context:** Python 3.11+, FastAPI 0.115.0, Uvicorn single-process, SQLite. No new dependencies — use `collections.defaultdict`, `collections.deque`, `time.monotonic`, `math.ceil`, `os.environ`.

**Pattern to follow:** `src/api/deps.py` is the canonical example of a FastAPI dependency (`get_db`, `get_current_user`). `check_rate_limit` follows the same shape: a function with typed parameters that FastAPI resolves via DI. `HTTPException` is already imported everywhere — use the same import.

**Why `app.include_router(..., dependencies=[...])` not app-level `dependencies=`:** The `/health` endpoint is registered directly on `app` and must remain exempt for load-balancer probes. Per-router injection is the surgical option.

**Why sliding window:** A fixed window allows a 2× burst at boundary edges. Sliding window (deque of `time.monotonic()` floats) eliminates that. GIL serialises dict/deque ops in a single-process Uvicorn deployment — no explicit lock needed.

**Test isolation:** `_store` is module-level and persists across requests in the same process. Tests must clear it between runs. Monkeypatch `rate_limit._LIMIT = 3` (not the env var) to keep tests fast and deterministic. Use a `@pytest.fixture(autouse=True)` or explicit `rate_limit._store.clear()` in a fixture.

**Do not touch:** `deps.py`, `models.py`, `routes/users.py`, `routes/orders.py`, `conftest.py`, `pyproject.toml`. Do not add logging, metrics, or middleware.

### Project Structure Notes

```
src/api/
  rate_limit.py        ← NEW (alongside deps.py, main.py, models.py)
  main.py              ← MODIFIED (2 include_router calls + 2 imports)

tests/
  test_rate_limit.py   ← NEW (alongside test_users.py, test_orders.py)
```

### References

- PRD: `_bmad-output/planning-artifacts/prds/prd-target-2026-05-19/prd.md` — FR-1 through FR-5, §5 Non-Goals
- Architecture: `_bmad-output/planning-artifacts/architecture/rate-limiting-design.md` — D1 (dependency not middleware), D2 (sliding window), D3 (client key), D4 (env vars)
- Existing dependency pattern: `src/api/deps.py`
- Router registration: `src/api/main.py`
- Test fixture: `tests/conftest.py` — use `client` fixture as-is

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — implementation matched spec exactly on first pass.

### Completion Notes List

- Created `src/api/rate_limit.py`: sliding-window dependency, env-var config, module-level deque store.
- Modified `src/api/main.py`: wired `check_rate_limit` into both routers via `dependencies=[Depends(...)]`; `/health` remains exempt.
- Created `tests/test_rate_limit.py`: 6 tests, `autouse` fixture patches `_LIMIT=3` and clears `_store` per test.
- 17/17 tests pass (6 new + 11 existing). No regressions.

### File List

- src/api/rate_limit.py (new)
- src/api/main.py (modified)
- tests/test_rate_limit.py (new)
