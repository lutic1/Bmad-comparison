---
description: "Task list for API Rate Limiting feature"
---

# Tasks: API Rate Limiting

**Input**: Design documents from `specs/001-api-rate-limiting/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/rate-limit.md ✅

**Tests**: Included — mandated by constitution (≥80% line coverage, happy-path + error-path per changed file).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Include exact file paths in all task descriptions

---

## Phase 1: Setup

**Purpose**: Confirm baseline before making changes.

- [x] T001 Run `pytest` from repo root and confirm all existing tests pass

**Checkpoint**: Baseline confirmed — safe to proceed.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the rate-limiting module and wire it into the application. Both user stories depend on this phase.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 Create `src/api/rate_limit.py` — implement `RateLimiter(limit: int = 100, window_seconds: int = 60)` class with `._counts: dict[int, tuple[int, float]]` and `.check(user_id: int, response: Response) -> None` method (increments counter, sets `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers, raises `HTTPException(429)` with `Retry-After` header when limit exceeded); add `get_rate_limiter() -> RateLimiter` module-level singleton factory; add `check_rate_limit(response: Response, x_user_id: int | None = Header(default=None), limiter: RateLimiter = Depends(get_rate_limiter)) -> None` FastAPI dependency (returns early when `x_user_id` is None)
- [x] T003 [P] Update `tests/conftest.py` — import `get_rate_limiter` and `RateLimiter` from `api.rate_limit`; in the `client` fixture, add `app.dependency_overrides[get_rate_limiter] = lambda: RateLimiter()` before yielding; add a new `rate_limited_client` fixture (same structure as `client`) that overrides `get_rate_limiter` with `lambda: RateLimiter(limit=3, window_seconds=60)`
- [x] T004 [P] Update `src/api/main.py` — import `check_rate_limit` from `api.rate_limit` and `Depends` from `fastapi`; add `dependencies=[Depends(check_rate_limit)]` to both `app.include_router(users.router, ...)` and `app.include_router(orders.router, ...)` calls; leave `GET /health` unchanged

**Checkpoint**: Foundation ready. Run `pytest` — all existing tests must still pass before user story work begins.

---

## Phase 3: User Story 1 — Excess Requests Rejected (Priority: P1) 🎯 MVP

**Goal**: Clients that exceed the request quota receive HTTP 429 and are not served; other clients are unaffected.

**Independent Test**: Use `rate_limited_client` fixture (limit=3), make 4 requests as the same user, confirm request 4 returns 429 while a different user's request still returns 200.

### Tests for User Story 1

- [x] T005 [P] [US1] Add test `test_request_within_quota_is_allowed` — using `rate_limited_client` and a seeded user, assert first request returns 200 in `tests/test_rate_limit.py`
- [x] T006 [P] [US1] Add test `test_request_exceeding_quota_returns_429` — using `rate_limited_client`, make `limit+1` requests as the same user, assert the last returns 429 in `tests/test_rate_limit.py`
- [x] T007 [P] [US1] Add test `test_429_body_detail` — assert 429 response JSON is `{"detail": "rate limit exceeded"}` in `tests/test_rate_limit.py`
- [x] T008 [P] [US1] Add test `test_client_counters_are_independent` — exhaust user A's quota, then assert a request from user B returns 200 in `tests/test_rate_limit.py`
- [x] T009 [P] [US1] Add test `test_unauthenticated_request_returns_401_not_429` — send request with no `X-User-Id` header to a protected route, assert 401 (not 429) in `tests/test_rate_limit.py`

**Checkpoint**: US1 fully functional and independently testable. `pytest tests/test_rate_limit.py` tests T005–T009 must all pass.

---

## Phase 4: User Story 2 — Rate Limit Transparency via Headers (Priority: P2)

**Goal**: Every API response includes accurate `X-RateLimit-*` headers; 429 responses include `Retry-After`.

**Independent Test**: Make any request with a valid `X-User-Id`, inspect response headers for `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`; make a second request and confirm `X-RateLimit-Remaining` decremented by 1.

### Tests for User Story 2

- [x] T010 [P] [US2] Add test `test_rate_limit_headers_present_on_200` — assert response contains `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers with correct types in `tests/test_rate_limit.py`
- [x] T011 [P] [US2] Add test `test_remaining_decrements_per_request` — make 3 requests, assert `X-RateLimit-Remaining` decreases by 1 on each response in `tests/test_rate_limit.py`
- [x] T012 [P] [US2] Add test `test_429_includes_retry_after_and_zero_remaining` — assert 429 response has `Retry-After` header (positive integer) and `X-RateLimit-Remaining: 0` in `tests/test_rate_limit.py`
- [x] T013 [US2] Add test `test_window_reset_clears_counter` — exhaust quota, set `limiter._counts[user_id]` tuple's `window_start` to `time.time() - window_seconds - 1` to simulate expiry, assert next request succeeds with `X-RateLimit-Remaining` back near `limit` in `tests/test_rate_limit.py`

**Checkpoint**: US1 and US2 both independently functional. `pytest tests/test_rate_limit.py` — all 9 tests must pass.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across the full test suite.

- [x] T014 Run `pytest` from repo root and confirm all tests (existing + new) pass with no failures
- [x] T015 [P] Verify `X-RateLimit-*` headers are absent on `GET /health` response (no `X-User-Id` required, rate limiter skips unauthenticated requests)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — run immediately
- **Foundational (Phase 2)**: Depends on Setup — **blocks both user stories**
  - T002 must complete before T003 and T004 (both import from `api.rate_limit`)
  - T003 and T004 are independent of each other — can run in parallel
- **User Story 1 (Phase 3)**: Depends on all of Phase 2 — T005–T009 can all run in parallel
- **User Story 2 (Phase 4)**: Depends on Phase 2 — T010–T012 can run in parallel; T013 depends on understanding T010–T012 patterns
- **Polish (Phase 5)**: Depends on all user story phases being complete

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2 complete — no dependency on US2
- **US2 (P2)**: Starts after Phase 2 complete — headers are set inside the same `RateLimiter.check()` call as enforcement, so US2 implementation is already done by T002; Phase 4 is tests only

### Parallel Opportunities

- T003 and T004 (Phase 2): different files — run in parallel after T002
- T005–T009 (Phase 3): all add test functions to `tests/test_rate_limit.py` — logically independent, best written sequentially to avoid conflicts in a single file
- T010–T012 (Phase 4): same file caveat as above

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. Phase 1: Confirm baseline
2. Phase 2: Build `rate_limit.py`, update `conftest.py` and `main.py`
3. Phase 3: Write US1 tests (T005–T009)
4. **STOP and VALIDATE**: `pytest tests/test_rate_limit.py` — all US1 tests pass, existing tests unbroken
5. Ship: rate limiting enforcement is live

### Full Delivery

1. MVP above
2. Phase 4: Write US2 tests (T010–T013) — headers are already implemented in T002, these are verification only
3. Phase 5: Full suite validation

---

## Notes

- `[P]` tasks operate on different logical units; however T005–T009 and T010–T013 all modify `tests/test_rate_limit.py` — implement sequentially within each phase to avoid merge conflicts
- `rate_limited_client` fixture uses `limit=3` to make quota exhaustion testable with minimal requests
- `test_window_reset` (T013) requires direct state manipulation of `limiter._counts` — access the limiter via `app.dependency_overrides[get_rate_limiter]()`
- No route files (`src/api/routes/`) are modified — changes are isolated to `rate_limit.py`, `main.py`, and `conftest.py`
