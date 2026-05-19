# Implementation Plan: API Rate Limiting

**Branch**: `001-api-rate-limiting` | **Date**: 2026-05-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-api-rate-limiting/spec.md`

## Summary

Add per-scope (user or IP) fixed-window rate limiting to all API endpoints via
FastAPI middleware. Clients exceeding 100 requests per 60-second window receive a
429 response with a retry signal. All responses carry `X-RateLimit-*` headers.
Implemented entirely with Python stdlib — no new dependencies.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI 0.115.0, Pydantic v2 (stdlib `time`, `threading` only
for rate limiting — no new packages)

**Storage**: In-memory dict (process-local, does not survive restart — acceptable per spec)

**Testing**: pytest 8.3.3 with existing `client` fixture from `tests/conftest.py`

**Target Platform**: Linux/macOS server (uvicorn)

**Project Type**: web-service

**Performance Goals**: Rate limit check adds no measurable latency to normal requests
(in-memory dict lookup + lock acquisition, O(1))

**Constraints**: No new third-party dependencies; middleware must not touch the database;
must not break existing tests

**Scale/Scope**: Single-process service; in-memory state is sufficient

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Stack: Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest | ✅ Pass | All existing stack; no deviations |
| Idiomatic FastAPI: small route functions, Pydantic models, Depends | ✅ Pass | Middleware layer; no route changes; `RateLimitError` Pydantic model for 429 body |
| Tests non-optional; 80% coverage; happy-path + error-path per route | ✅ Pass | `tests/test_rate_limiter.py` will cover both paths |
| Conventional commits | ✅ Pass | Commit will use `feat: add API rate limiting` |
| No new third-party dependencies without justification | ✅ Pass | Stdlib only (`time`, `threading`) |
| Type hints on every public function and route handler | ✅ Pass | Middleware dispatch method and all helpers typed |
| Don't refactor unrelated code | ✅ Pass | Only `main.py` (add_middleware call) and new files touched |

**Post-design re-check**: All gates pass. No Complexity Tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/001-api-rate-limiting/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── rate-limit-headers.md
│   └── rate-limit-error.md
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
src/api/
├── middleware/
│   └── rate_limiter.py      # NEW: RateLimiterMiddleware + RateLimitError schema
├── main.py                  # MODIFIED: app.add_middleware(RateLimiterMiddleware, ...)
├── models.py                # unchanged
├── deps.py                  # unchanged
└── routes/
    ├── users.py             # unchanged
    └── orders.py            # unchanged

tests/
├── conftest.py              # unchanged
├── test_rate_limiter.py     # NEW: rate limiter tests
├── test_users.py            # unchanged (regression check)
└── test_orders.py           # unchanged (regression check)
```

**Structure Decision**: Single project layout (existing). Rate limiter lives in
`src/api/middleware/rate_limiter.py` — the directory was already created and empty,
signalling this location was anticipated. No new top-level directories.
