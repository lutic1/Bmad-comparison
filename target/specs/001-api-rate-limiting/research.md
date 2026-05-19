# Research: API Rate Limiting

**Feature**: `001-api-rate-limiting`
**Date**: 2026-05-19

## Decision 1: Rate-Limit Algorithm

**Decision**: Fixed (tumbling) window counter.

**Rationale**: The spec states "fixed sliding or tumbling time window". Tumbling window
is the simplest correct implementation — each scope gets a fresh counter at the start
of every 60-second window. The count is deterministic and easy to reason about in tests.

**Alternatives considered**:
- Sliding window log: fair but O(n) memory per scope per window; no benefit for this service.
- Token bucket: smoother burst control but harder to expose "remaining" count correctly.
- Leaky bucket: suited for rate-shaping, not hard limits; wrong fit here.

## Decision 2: Storage Mechanism

**Decision**: In-memory `dict` keyed on `(scope, window_start_unix)` → request count,
protected by a `threading.Lock`.

**Rationale**: The spec explicitly allows in-memory storage (assumption: "does not need
to survive a service restart"). No external dependencies are needed; `time` and
`threading` are stdlib. The `threading.Lock` prevents race conditions under uvicorn's
threaded worker model.

**Alternatives considered**:
- Redis: required for multi-process/distributed deployments, but out of scope here.
- SQLite: would survive restarts but adds unnecessary I/O overhead for a hot-path check.

## Decision 3: Implementation Layer

**Decision**: FastAPI `BaseHTTPMiddleware` in `src/api/middleware/rate_limiter.py`,
registered via `app.add_middleware()` in `main.py`.

**Rationale**: FR-004 requires rate limiting on ALL endpoints without each route opting
in. Middleware is the correct layer — it intercepts every request before it reaches any
route handler. The project already has an empty `src/api/middleware/` directory, which
signals this was anticipated. No route files need to be touched.

**Alternatives considered**:
- FastAPI `Depends()` per route: violates FR-004 (would require modifying every route).
- ASGI middleware at server level: possible but harder to test with FastAPI's TestClient.

## Decision 4: Scope Identification

**Decision**: Check the `X-User-Id` request header first; fall back to
`request.client.host` (IP address) if the header is absent.

**Rationale**: Matches FR-005 exactly. Reuses the existing `X-User-Id` convention from
`deps.py` without coupling middleware to the database. The middleware does NOT validate
that the user ID exists — it trusts the header value as a scope key. Route-level auth
remains responsible for validating user identity.

**Alternatives considered**:
- IP-only: loses per-user fairness and would allow a single user to exhaust a shared IP quota.
- Coupling to `get_current_user` dep: would require a DB call in every middleware pass —
  adds latency and tight coupling.

## Decision 5: Response Headers

**Decision**: Attach the following headers to every response (including 429s):

| Header                  | Value                                         |
|-------------------------|-----------------------------------------------|
| `X-RateLimit-Limit`     | Configured quota (e.g. `100`)                 |
| `X-RateLimit-Remaining` | Remaining requests in current window          |
| `X-RateLimit-Reset`     | Unix timestamp when the current window resets |
| `Retry-After`           | Seconds until reset (429 responses only)      |

**Rationale**: These four headers are the de-facto standard (used by GitHub, Stripe,
Twitter/X). They cover FR-002 and FR-003 fully. `Retry-After` is included only on 429
responses per RFC 6585.

**Alternatives considered**:
- `RateLimit-*` (IETF draft): not yet widely adopted; `X-RateLimit-*` is universally
  understood.

## Decision 6: 429 Response Body

**Decision**: JSON body `{"detail": "Rate limit exceeded", "retry_after": <int>}`.

**Rationale**: Consistent with FastAPI's built-in error format (`{"detail": "..."}`)
used by existing routes (e.g. 404, 409, 401 responses). Adding `retry_after` gives
clients the seconds-until-reset value in the body as well as the `Retry-After` header.

## Decision 7: Configuration

**Decision**: Middleware accepts `limit` (int, default 100) and `window_seconds` (int,
default 60) constructor parameters. Registered in `main.py` with explicit values so the
defaults are visible at the call site.

**Rationale**: No additional config system is needed. The spec treats these as
configurable values, not hard-coded business rules. Constructor params make the
middleware independently testable with arbitrary limits.

## No New Dependencies Required

All implementation uses Python stdlib (`time`, `threading`, `collections`) and FastAPI's
built-in `BaseHTTPMiddleware`. The constitution's "No new third-party dependencies
without a stated justification" principle is satisfied.
