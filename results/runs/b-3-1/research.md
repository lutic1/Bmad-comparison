# Research: API Rate Limiting

**Feature**: 001-api-rate-limiting
**Date**: 2026-05-18

---

## Decision 1: Rate Limiting Algorithm

**Decision**: Fixed window counter

**Rationale**: The simplest algorithm that satisfies the spec. Each client gets a counter and a window start time. When the window expires the counter resets. This is trivially implementable with a plain `dict` — no third-party dependency required and no background threads needed for cleanup.

**Alternatives considered**:
- *Sliding window log*: Stores a timestamp per request; more accurate at window boundaries but higher memory use and complexity. Not justified for this service's scale (single instance, in-memory).
- *Token bucket*: Smooth burst handling; overkill for a simple per-user global limit.
- *slowapi (third-party)*: Wraps `limits` library; adds two transitive dependencies and significant surface area for a problem solvable in ~30 lines of stdlib code. Constitution principle V prohibits new deps without justification.

---

## Decision 2: State Storage

**Decision**: In-memory `dict` on a module-level singleton (`RateLimiter` instance)

**Rationale**: The spec explicitly states state does not need to survive server restarts and the service runs as a single instance. A module-level object is zero-cost to set up, requires no infrastructure, and is reset naturally on restart.

**Alternatives considered**:
- *Redis*: Would survive restarts and support horizontal scaling; the spec rules this out for current scope.
- *SQLite (existing DB)*: Possible but introduces write contention and schema changes for a transient counter — wasteful.

---

## Decision 3: FastAPI Integration Point

**Decision**: `Depends(check_rate_limit)` injected at router include time in `main.py`

**Rationale**: Applying the dependency at `app.include_router(..., dependencies=[Depends(check_rate_limit)])` enforces rate limiting on all routes under each router without touching any individual route function. The `check_rate_limit` dependency receives `Response` (to set headers) and `X-User-Id` (to identify the client) directly — no coupling to auth logic.

The `/health` endpoint is excluded by being registered directly on `app`, not via a router. This is consistent with it being a public, unauthenticated endpoint.

**Alternatives considered**:
- *ASGI middleware*: Runs earlier in the stack but is harder to test (cannot be overridden via `app.dependency_overrides`) and bypasses FastAPI's header injection model.
- *Per-route `Depends`*: Would require touching every route file — violates constitution principle VII (Focused Changes).

---

## Decision 4: Client Identity Key

**Decision**: `x_user_id` integer from the `X-User-Id` header

**Rationale**: This matches the existing authentication pattern (`get_current_user` in `deps.py`). Unauthenticated requests (no `X-User-Id`) are passed through by the rate limiter; the existing auth dependency on protected routes rejects them before any business logic runs.

**Alternatives considered**:
- *IP address*: Not available in FastAPI without middleware; also incorrect for shared-NAT clients.
- *API key*: No API key concept exists in this service.

---

## Decision 5: Default Limit Values

**Decision**: 100 requests per 60-second window

**Rationale**: Standard industry default for web service rate limiting (matches GitHub API, Stripe, and similar services). Documented in spec assumptions. Configurable at instantiation time for test overrides.

---

## Decision 6: Response Headers

**Decision**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`

**Rationale**: De-facto standard headers used by GitHub, Twitter, Stripe, and the IETF draft for rate limit headers (RFC 6585 for 429, `Retry-After` is standardized). `X-RateLimit-Reset` is a Unix timestamp (seconds since epoch). `Retry-After` is seconds until the window resets, included only on 429 responses.
