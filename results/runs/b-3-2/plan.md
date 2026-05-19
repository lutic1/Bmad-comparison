# Implementation Plan: API Rate Limiting

**Branch**: `001-api-rate-limiting` | **Date**: 2026-05-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-api-rate-limiting/spec.md`

## Summary

Add a fixed-window rate limiter to the FastAPI service via
`BaseHTTPMiddleware`. Every response gains `X-RateLimit-*` headers;
requests beyond the configured quota receive HTTP 429 with `Retry-After`.
Client identity uses `X-User-Id` when present, falling back to client IP.
State is in-memory (no DB). Configurable via environment variables.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI 0.115.0, Starlette `BaseHTTPMiddleware`
(bundled with FastAPI — no new dependencies), stdlib `threading`, `time`,
`os`, `collections`

**Storage**: In-memory dict (`RateLimitStore`) — state does not persist
across restarts (per spec assumption)

**Testing**: pytest, Starlette `TestClient` via existing `client` fixture

**Target Platform**: Linux/macOS server (web-service)

**Project Type**: web-service

**Performance Goals**: Rate limit check MUST add negligible overhead
(dict lookup + lock acquire; no I/O)

**Constraints**: No new third-party dependencies (Constitution V);
stdlib only for rate limit implementation

**Scale/Scope**: All endpoints, all clients, single process

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Technology Stack | ✅ PASS | Python 3.11+, FastAPI, pytest — no deviation |
| II. Idiomatic API Design | ✅ PASS | `BaseHTTPMiddleware` is the idiomatic FastAPI pattern for cross-cutting concerns; Pydantic not needed (no new request/response schemas beyond the 429 body) |
| III. Testing (NON-NEGOTIABLE) | ✅ PASS | `tests/test_rate_limit.py` will ship with happy-path and error-path tests for each user story |
| IV. Commit Convention | ✅ PASS | Will use `feat: add rate limiting middleware` |
| V. Dependency Management | ✅ PASS | Zero new third-party dependencies; `BaseHTTPMiddleware` is part of Starlette which is already a FastAPI transitive dependency |
| VI. Type Safety | ✅ PASS | All public functions and the middleware class will carry full type hints |
| VII. Change Scope | ✅ PASS | Only `src/api/middleware/`, `src/api/main.py` (one line), and `tests/test_rate_limit.py` are touched |

**Post-design re-check**: All gates still pass. The middleware design
introduces no new ORM models, no migrations, and no route changes.

## Project Structure

### Documentation (this feature)

```text
specs/001-api-rate-limiting/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 — algorithm and design decisions
├── data-model.md        # Phase 1 — in-memory state model
├── quickstart.md        # Phase 1 — manual validation guide
├── contracts/
│   └── rate-limit-headers.md   # HTTP header contract
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
src/api/
├── main.py                      # Modified: register RateLimitMiddleware
├── middleware/
│   ├── __init__.py              # New (empty)
│   └── rate_limit.py            # New: RateLimitStore + RateLimitMiddleware

tests/
└── test_rate_limit.py           # New: rate limit tests
```

**Structure Decision**: Single-project layout. The middleware lives in
`src/api/middleware/` — a new sub-package parallel to `routes/` and
`utils/`, consistent with the existing layering in this repo.

## Complexity Tracking

> No Constitution violations — this section is intentionally empty.
