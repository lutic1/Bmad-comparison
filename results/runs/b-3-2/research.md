# Research: API Rate Limiting

**Feature**: 001-api-rate-limiting
**Date**: 2026-05-19

## Decision 1: Rate Limiting Algorithm

**Decision**: Fixed Window Counter

**Rationale**: Simplest approach that satisfies all spec requirements.
Each client gets a counter that resets at the end of every fixed time
window. No external dependencies; pure stdlib (`collections.defaultdict`,
`threading.Lock`, `time.time()`). Deterministic reset behaviour matches
FR-007 exactly.

**Alternatives considered**:
- *Sliding Window Log*: More accurate (avoids burst at window boundary)
  but requires storing per-request timestamps — higher memory per client,
  more complexity. Spec does not require burst protection; rejected.
- *Token Bucket*: Smooths traffic, allows short bursts. Requires float
  arithmetic for token replenishment and is harder to test deterministically.
  No spec requirement for burst tolerance; rejected.
- *Leaky Bucket*: Enforces a constant outflow rate. Overly strict for a
  REST API where bursty-but-bounded usage is normal; rejected.

## Decision 2: Implementation Placement

**Decision**: FastAPI `BaseHTTPMiddleware`

**Rationale**: Rate limiting is a cross-cutting concern that MUST apply to
every endpoint uniformly (per spec Assumption 1). Middleware intercepts
every request before it reaches any route handler, adding headers on the
way out. The CLAUDE.md "What not to do" clause about middleware includes
the qualifier "unless the task asks for it" — this task does.

**Alternatives considered**:
- *FastAPI dependency (`Depends`)* appended to every router: Requires
  modifying every route signature, which violates Constitution Principle VII
  (don't change unrelated code in the same change). Also fragile — new
  routes could accidentally omit the dependency.
- *`app.middleware("http")` decorator*: Functionally equivalent to
  `BaseHTTPMiddleware` but less testable (no class to instantiate with
  custom args in tests). `BaseHTTPMiddleware` is idiomatic FastAPI.

## Decision 3: Client Identity Key

**Decision**: `X-User-Id` header value (when present); falls back to
`request.client.host` (IP address) for unauthenticated requests.

**Rationale**: Matches the existing auth pattern in `deps.py` and satisfies
FR-005. Identified users have a stable, unambiguous key. Unauthenticated
clients share a namespace (`ip:{address}`) to avoid collisions with integer
user IDs.

**Alternatives considered**:
- *IP-only*: Would merge authenticated and unauthenticated quotas for users
  behind the same IP; violates per-client isolation (FR-004).
- *Combined key (user_id + IP)*: Overly complex; the spec requires
  isolation by identity, not by identity-and-location.

## Decision 4: State Storage

**Decision**: Module-level `RateLimitStore` — `dict[str, (count, window_start)]`
protected by `threading.Lock`.

**Rationale**: Spec assumption explicitly states state does not need to
survive restarts. Stdlib-only; no third-party dependency (Constitution V).
`threading.Lock` is required because FastAPI (ASGI) may run sync middleware
dispatch in a thread pool.

**Alternatives considered**:
- *Redis*: Persistent, distributed. No spec requirement for persistence or
  distribution; adds a third-party dependency (violates Constitution V).
- *`asyncio.Lock`*: Appropriate only for pure async code. `BaseHTTPMiddleware`
  runs `dispatch` as a coroutine but the lock itself must be compatible with
  the threading model FastAPI uses for sync code paths; `threading.Lock` is
  safer.

## Decision 5: Configuration

**Decision**: Module-level constants with environment variable overrides:
- `RATE_LIMIT_REQUESTS` (default: `60`)
- `RATE_LIMIT_WINDOW_SECONDS` (default: `60`)

**Rationale**: Satisfies FR-006 (configurable without code changes) using
stdlib `os.environ`. No config file framework needed for two values.

## Decision 6: Response Headers

**Decision**: Use the de-facto standard `X-RateLimit-*` header names:
- `X-RateLimit-Limit` — total quota
- `X-RateLimit-Remaining` — requests remaining in window
- `X-RateLimit-Reset` — Unix timestamp (integer) when window resets
- `Retry-After` — seconds to wait; added only to 429 responses (RFC 6585)

**Rationale**: These names are the industry standard (GitHub, Stripe, etc.)
and are widely understood by HTTP clients. `Retry-After` is required by
RFC 6585 for 429 responses and satisfies FR-003.
