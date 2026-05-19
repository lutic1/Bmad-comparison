---
description: "Task list for API Rate Limiting feature implementation"
---

# Tasks: API Rate Limiting

**Input**: Design documents from `specs/001-api-rate-limiting/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Per the project constitution, tests are MANDATORY — every new route ships
with a happy-path and at least one error-path test, with minimum 80% line coverage
on changed files.

**Organization**: Tasks are grouped by user story to enable independent implementation
and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Exact file paths are included in all descriptions

## Path Conventions

- Single project layout: `src/api/` and `tests/` at repository root
- New file: `src/api/middleware/rate_limiter.py`
- Modified file: `src/api/main.py`
- New test file: `tests/test_rate_limiter.py`

---

## Phase 1: Setup

**Purpose**: Create the middleware module files so subsequent tasks have a home.

- [x] T001 Create `src/api/middleware/__init__.py` (empty file to make middleware a package)
- [x] T002 [P] Create `src/api/middleware/rate_limiter.py` with `RateLimitError` Pydantic model (`detail: str`, `retry_after: int`) and `RateLimiterMiddleware` class skeleton with `__init__(self, app, limit: int = 100, window_seconds: int = 60)`, `_counters: dict`, and `_lock: threading.Lock`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement the shared helper methods that both user stories depend on.
No user story work can begin until this phase is complete.

- [x] T003 Implement `_get_scope(request) -> str` in `src/api/middleware/rate_limiter.py` — returns `f"user:{X-User-Id value}"` if the `X-User-Id` header is present, else `f"ip:{request.client.host}"`
- [x] T004 Implement `_get_window_start(self) -> int` in `src/api/middleware/rate_limiter.py` — returns `int(time.time() // self.window_seconds) * self.window_seconds`

**Checkpoint**: Middleware helpers ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - Client Blocked When Quota Exceeded (Priority: P1) 🎯 MVP

**Goal**: When a client exceeds their quota, they receive a 429 response with a
`Retry-After` signal telling them when they can resume.

**Independent Test**: `pytest tests/test_rate_limiter.py -k "exceed or blocked or reset"`

> **NOTE: Write test tasks T005–T007 FIRST and confirm they FAIL before implementing T008–T009**

### Tests for User Story 1 (MANDATORY per constitution)

- [x] T005 [US1] Write test `test_request_over_limit_returns_429`: configure middleware with `limit=2`, make 3 requests from the same scope, assert the third returns HTTP 429 with body `{"detail": "Rate limit exceeded", "retry_after": <positive int>}` in `tests/test_rate_limiter.py`
- [x] T006 [US1] Write test `test_429_includes_retry_after_header_and_zero_remaining`: assert a rate-limited response includes `Retry-After` header and `X-RateLimit-Remaining: 0` in `tests/test_rate_limiter.py`
- [x] T007 [US1] Write test `test_scope_allowed_after_window_reset`: patch `time.time` to advance past the window boundary, assert the previously-blocked scope receives 200 on the next request in `tests/test_rate_limiter.py`

### Implementation for User Story 1

- [x] T008 [US1] Implement `RateLimiterMiddleware.dispatch()` in `src/api/middleware/rate_limiter.py` — acquire `_lock`, compute scope and window start, increment counter, if count exceeds `limit` return `JSONResponse(RateLimitError(...).model_dump(), status_code=429)` with `Retry-After` and all `X-RateLimit-*` headers; otherwise call `await call_next(request)` and proceed
- [x] T009 [US1] Register middleware in `src/api/main.py`: add `app.add_middleware(RateLimiterMiddleware, limit=100, window_seconds=60)` after the existing imports and before router inclusion

**Checkpoint**: US1 independently functional — clients hitting the limit receive 429 with a retry signal.

---

## Phase 4: User Story 2 - Client Can Monitor Remaining Quota (Priority: P2)

**Goal**: Every API response (including 200s) carries `X-RateLimit-Limit`,
`X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers so clients can proactively
manage their request rate.

**Independent Test**: `pytest tests/test_rate_limiter.py -k "header or remaining or scope or fallback"`

> **NOTE: Write test tasks T010–T013 FIRST and confirm they FAIL before implementing T014**

### Tests for User Story 2 (MANDATORY per constitution)

- [x] T010 [US2] Write test `test_200_response_includes_ratelimit_headers`: assert a normal (within-quota) response includes `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers with integer-string values in `tests/test_rate_limiter.py`
- [x] T011 [US2] Write test `test_remaining_decrements_per_request`: configure `limit=5`, make 3 requests from the same scope, assert `X-RateLimit-Remaining` reads `4`, `3`, `2` on successive responses in `tests/test_rate_limiter.py`
- [x] T012 [US2] Write test `test_independent_scopes_have_independent_counters`: make requests with `X-User-Id: 1` and `X-User-Id: 2` interleaved, assert each scope's `X-RateLimit-Remaining` decrements independently in `tests/test_rate_limiter.py`
- [x] T013 [US2] Write test `test_ip_fallback_scope_when_no_user_header`: make a request with no `X-User-Id` header, assert `X-RateLimit-Remaining` is present and decrements on the second headerless request in `tests/test_rate_limiter.py`

### Implementation for User Story 2

- [x] T014 [US2] Extend the pass-through path in `RateLimiterMiddleware.dispatch()` in `src/api/middleware/rate_limiter.py` — after `await call_next(request)` returns, mutate the response to add `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers before returning it

**Checkpoint**: US1 and US2 both independently functional — all responses carry quota headers.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Regression verification and end-to-end validation.

- [x] T015 Run `pytest` (full suite) and confirm all rate limiter tests pass and no regressions in `tests/test_users.py`, `tests/test_orders.py`, `tests/test_dates.py`
- [ ] T016 [P] Follow all curl validation steps in `specs/001-api-rate-limiting/quickstart.md` against a running `uvicorn api.main:app` server to confirm end-to-end behavior

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — T001 and T002 can start immediately and run in parallel
- **Foundational (Phase 2)**: Depends on Phase 1 (T003 and T004 require the file from T002) — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase; write T005–T007 first (failing tests), then T008–T009
- **User Story 2 (Phase 4)**: Depends on Phase 3 (T014 extends the `dispatch()` implemented in T008); write T010–T013 first (failing tests), then T014
- **Polish (Phase 5)**: Depends on both user stories complete

### User Story Dependencies

- **US1 (P1)**: Unblocks after Foundational complete. No dependency on US2.
- **US2 (P2)**: Depends on US1 (extends the same `dispatch()` method written in T008).

### Within Each User Story

- Tests MUST be written and FAIL before implementation (non-optional per constitution)
- Helpers (`_get_scope`, `_get_window_start`) before `dispatch()`
- `dispatch()` before `add_middleware` registration
- Registration before end-to-end validation

### Parallel Opportunities

- T001 and T002 can run in parallel (different new files, no dependencies)
- T016 can run in parallel with any non-server-running task in Phase 5

---

## Parallel Example: Setup Phase

```bash
# Launch both setup tasks together (different files, no deps):
Task: "Create src/api/middleware/__init__.py"           # T001
Task: "Create src/api/middleware/rate_limiter.py ..."   # T002
```

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks everything)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: `pytest tests/test_rate_limiter.py -k "exceed or blocked or reset"`
5. Rate limiting is live and enforced — shippable MVP

### Incremental Delivery

1. Setup + Foundational → middleware module exists
2. US1 → 429 enforcement live → deploy/demo (MVP)
3. US2 → quota headers on all responses → deploy/demo
4. Polish → full regression + quickstart validation

---

## Notes

- `[P]` tasks touch different files with no mutual dependencies
- `[Story]` label maps each task to the user story it serves
- TDD ordering is required by constitution: tests before implementation within each phase
- `dispatch()` is a single method — T008 (enforcement path) and T014 (header injection path) are additive changes to the same function; T014 depends on T008
- No database changes; no new dependencies; `src/api/middleware/` dir already exists
