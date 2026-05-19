---
description: "Task list for API Rate Limiting implementation"
---

# Tasks: API Rate Limiting

**Input**: Design documents from `/specs/001-api-rate-limiting/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in every task description

## Path Conventions

- Single project: `src/`, `tests/` at repository root

---

## Phase 1: Setup

**Purpose**: Create the middleware package so subsequent tasks can add files to it.

- [x] T001 Create `src/api/middleware/__init__.py` (empty file, establishes the package)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement the rate limit store and middleware class — required before
any user story can be verified.

**⚠️ CRITICAL**: No user story test phase can begin until this phase is complete.

- [x] T002 Implement `RateLimitStore` in `src/api/middleware/rate_limit.py`:
  read `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS` from env (defaults 60/60);
  store per-client fixed-window counters in a `dict[str, tuple[int, float]]` protected
  by `threading.Lock`; expose a `check_and_increment(key: str) -> tuple[bool, int, float]`
  method that returns `(allowed, remaining, window_reset_ts)`

- [x] T003 Implement `RateLimitMiddleware(BaseHTTPMiddleware)` in
  `src/api/middleware/rate_limit.py` (depends on T002):
  extract client key from `X-User-Id` header (string) when present, else
  `"ip:{request.client.host}"`; call `RateLimitStore.check_and_increment`; on allowed
  requests call `call_next` and add `X-RateLimit-Limit`, `X-RateLimit-Remaining`,
  `X-RateLimit-Reset` headers; on denied requests return a 429 `JSONResponse`
  `{"detail": "Rate limit exceeded"}` with those headers plus `Retry-After`
  (seconds until window reset, ceiling-rounded)

- [x] T004 Register `RateLimitMiddleware` in `src/api/main.py` (depends on T003):
  add `app.add_middleware(RateLimitMiddleware)` after the `FastAPI()` instantiation

**Checkpoint**: Service starts, all existing endpoints respond, and
`curl -si http://localhost:8000/health` shows `X-RateLimit-*` headers.

---

## Phase 3: User Story 1 — Throttling Enforcement (Priority: P1) 🎯 MVP

**Goal**: Prove that requests beyond the quota are rejected with HTTP 429 and
that the quota resets at the end of the window.

**Independent Test**: Configure a limit of 2, send 3 requests, confirm the third
returns 429, wait for the window to expire, confirm the next request returns 200.

### Tests for User Story 1

- [x] T005 [US1] Write throttle enforcement tests in `tests/test_rate_limit.py`:
  - `test_request_within_limit_succeeds` — with limit=2, first two requests return 200
  - `test_request_exceeding_limit_returns_429` — third request returns 429 with
    `{"detail": "Rate limit exceeded"}`
  - `test_window_reset_allows_requests_again` — after the window expires the
    previously throttled client receives 200 again

**Checkpoint**: `pytest tests/test_rate_limit.py -k "us1 or within_limit or exceeding_limit or window_reset"` passes.

---

## Phase 4: User Story 2 — Rate Limit Status Visibility (Priority: P2)

**Goal**: Prove that every API response carries the full rate limit header set and
that the 429 response additionally includes `Retry-After`.

**Independent Test**: Issue one request and assert all three `X-RateLimit-*`
headers are present; exhaust the limit and assert `Retry-After` appears on the
429 response.

### Tests for User Story 2

- [x] T006 [US2] Write header visibility tests in `tests/test_rate_limit.py`
  (append to file from T005):
  - `test_rate_limit_headers_present_on_success` — response includes
    `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
  - `test_remaining_decrements_per_request` — `X-RateLimit-Remaining` decreases
    by 1 with each successive request
  - `test_429_includes_retry_after` — throttled response includes `Retry-After`
    with a positive integer value

**Checkpoint**: `pytest tests/test_rate_limit.py -k "header or remaining or retry"` passes.

---

## Phase 5: User Story 3 — Per-Client Isolation (Priority: P3)

**Goal**: Prove that exhausting one client's quota has zero effect on a different
client's ability to make requests.

**Independent Test**: Exhaust the quota for `X-User-Id: 1`; assert `X-User-Id: 2`
still receives 200. Then exhaust an unauthenticated (IP-based) client's quota and
assert an authenticated client is unaffected.

### Tests for User Story 3

- [x] T007 [US3] Write per-client isolation tests in `tests/test_rate_limit.py`
  (append to file from T006):
  - `test_throttled_user_does_not_affect_other_user` — exhaust quota for user 1,
    confirm user 2 gets 200
  - `test_authenticated_and_unauthenticated_clients_are_isolated` — exhaust the
    unauthenticated (IP) quota, confirm an authenticated user-id request still
    succeeds

**Checkpoint**: `pytest tests/test_rate_limit.py -k "isolation or other_user or unauthenticated"` passes.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Confirm the full test suite is green and no existing behaviour regressed.

- [x] T008 Run `pytest` (full suite) and confirm all tests pass, including
  pre-existing `test_users.py`, `test_orders.py`, and `test_dates.py`

- [x] T009 Validate against `specs/001-api-rate-limiting/quickstart.md` checklist:
  confirm headers appear on a live `GET /health`, 429 is returned after limit
  exceeded, and per-client isolation holds manually

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **blocks all story phases**
- **US1 (Phase 3)**: Depends on Phase 2 — can start once middleware is registered
- **US2 (Phase 4)**: Depends on Phase 2 — can start in parallel with Phase 3
  (different test functions, same file — coordinate if pairing)
- **US3 (Phase 5)**: Depends on Phase 2 — can start in parallel with Phases 3 & 4
- **Polish (Phase 6)**: Depends on all story phases complete

### Within Each Phase

- T002 → T003 → T004 (strictly sequential; same file then main.py)
- T005 → T006 → T007 (sequential; all append to `tests/test_rate_limit.py`)

### Parallel Opportunities

- Once Phase 2 is done, Phases 3, 4, and 5 can proceed in parallel if
  different developers coordinate commits to `tests/test_rate_limit.py`
- T008 and T009 (Polish) can run in parallel

---

## Implementation Strategy

### MVP (User Story 1 only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002 → T003 → T004)
3. Complete Phase 3: US1 tests (T005)
4. **STOP and VALIDATE**: `pytest tests/test_rate_limit.py`
5. Clients are now protected from overload — MVP shippable

### Incremental Delivery

1. Setup + Foundational → middleware live, headers visible
2. + US1 tests → throttling verified
3. + US2 tests → header contract verified
4. + US3 tests → isolation verified
5. Polish → full regression confirmed

---

## Notes

- `[P]` is omitted on T005–T007 because they all write to the same file
  (`tests/test_rate_limit.py`); sequence them or coordinate carefully
- Override `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS` in the
  `client` fixture via `monkeypatch.setenv` or by patching module constants
  so tests run at a low limit (e.g. 2) without waiting 60 seconds for resets
- The existing `client` fixture in `tests/conftest.py` is sufficient —
  no new fixtures are needed
- `app.add_middleware` in `main.py` must come **after** `app = FastAPI(...)`
  but **before** any `app.include_router(...)` calls to ensure the middleware
  wraps all routes
