---
title: API Rate Limiting
status: final
created: 2026-05-19
updated: 2026-05-19
---

# PRD: API Rate Limiting

## 0. Document Purpose

This PRD is for the PM, architect, and the engineer implementing the change. It defines requirements for adding rate limiting to the existing FastAPI service (users + orders, SQLAlchemy + SQLite). It builds on the project guardrails in `CLAUDE.md` and the service description in the project `CLAUDE.md`. No prior UX or architecture documents exist for this feature.

All assumptions made in the absence of stakeholder input are tagged `[ASSUMPTION]` and collected in §9.

---

## 1. Vision

The service currently accepts requests without any throttle, leaving it vulnerable to accidental hammering by misconfigured clients and deliberate abuse by malicious ones. Without a limit, a single caller can exhaust server resources, degrade response times for all other users, and surface bugs in downstream SQLite that appear only under write contention.

Rate limiting introduces a per-caller ceiling on request frequency. When a caller exceeds the ceiling the service responds with a standard `429 Too Many Requests` and a `Retry-After` hint, giving well-behaved clients the information they need to back off gracefully while stopping bad actors from overwhelming the system.

The scope of v1 is deliberately narrow: a single, configurable global limit applied uniformly across all endpoints. No per-route tiers, no dashboards, no distributed state. The implementation must fit inside the existing stdlib-only dependency policy.

---

## 2. Target User

### 2.1 Primary Persona

**Internal API client** — a service, script, or developer hitting the API either programmatically or via a test harness. They know the `X-User-Id` contract and expect standard HTTP semantics on error.

### 2.2 Jobs To Be Done

- Call API endpoints at a normal, sustained rate without being blocked.
- Receive a clear, machine-readable signal when they have been throttled, including when to retry.
- Operate with zero configuration changes on their end as long as they stay within the limit.

### 2.3 Non-Users (v1)

- External / public internet callers (service is internal-only today).
- Operators wanting per-endpoint or per-role limit tiers (deferred, see §5).

### 2.4 Key User Journeys

**UJ-1. Client makes requests at a normal rate and is never blocked.**
A script with `X-User-Id: 42` calls `GET /orders` 30 times in a minute. All 30 return `200`. The rate limiter records the count but never fires. The script has zero awareness that limiting exists.

**UJ-2. Client exceeds the limit and recovers gracefully.**
The same script fires 70 requests in 60 seconds. Requests 1–60 succeed. Request 61 receives `429 Too Many Requests` with `Retry-After: 23` (seconds until the window resets). The script pauses, retries after 23 seconds, and succeeds. The next window starts fresh.

---

## 3. Glossary

- **Subject** — The entity whose request count is tracked. Determined by `X-User-Id` header when present; client IP address when not.
- **Window** — The fixed time period (in seconds) over which requests are counted. At window expiry, the counter resets to zero.
- **Limit** — The maximum number of requests a Subject may make within one Window.
- **429** — HTTP status code `429 Too Many Requests` (RFC 6585), returned when a Subject exceeds the Limit.
- **Retry-After** — HTTP response header whose value is the number of seconds until the current Window expires and the counter resets.

---

## 4. Features

### 4.1 Global Rate Limiter Middleware

**Description:** A FastAPI middleware layer intercepts every inbound HTTP request before it reaches any route handler. It identifies the Subject, increments a per-Subject counter for the current Window, and either allows the request to proceed or short-circuits it with a `429` response. [ASSUMPTION: a single global Limit applies to all endpoints equally — per-route tiers are out of scope for v1 (see OQ-1).] The middleware is registered once at application startup and requires no per-route decoration.

**Functional Requirements:**

#### FR-1: Subject identification

The middleware MUST identify the Subject from the `X-User-Id` request header when present. If the header is absent or empty, the Subject MUST fall back to the client IP address extracted from the ASGI `client` tuple. [ASSUMPTION: `X-Forwarded-For` or `X-Real-IP` proxy headers are not in use; raw socket IP is reliable (OQ-2).]

**Consequences (testable):**
- A request with `X-User-Id: 42` is tracked under key `user:42`, independent of source IP.
- A request with no `X-User-Id` is tracked under key `ip:<client-ip>`.
- Two requests from different IPs but the same `X-User-Id` share a single counter.

---

#### FR-2: Fixed-window counting

The middleware MUST count requests per Subject using a fixed-window algorithm. [ASSUMPTION: window duration is 60 seconds and Limit is 60 requests (OQ-3).] State MUST be held in-process (Python dict + `threading.Lock`); no external store is required or permitted in v1 (OQ-4). Window boundaries are wall-clock aligned to the start of the first request in each window per Subject.

**Consequences (testable):**
- Subject makes 60 requests in window N: all succeed.
- Subject makes request 61 in window N: receives `429`.
- Window expires; Subject makes 1 request in window N+1: succeeds.
- Counter is accurate under concurrent requests (no race conditions).

---

#### FR-3: 429 response shape

When a Subject exceeds the Limit, the middleware MUST return `429 Too Many Requests` with:
- `Retry-After: <integer>` header — seconds remaining until window reset, rounded up.
- `Content-Type: application/json` body: `{"detail": "Rate limit exceeded. Retry after <N> seconds."}`.

The response MUST NOT reach any route handler.

**Consequences (testable):**
- Response status is exactly `429`.
- `Retry-After` header is present, is an integer, and equals `⌈window_end − now⌉` seconds.
- Body is valid JSON matching the shape above.
- Route handler is not invoked (no DB query, no side-effects).

---

#### FR-4: Limit configurability

The Limit and Window MUST be configurable at startup via environment variables (`RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS`), with hard-coded defaults used when variables are absent. [ASSUMPTION: defaults are 60 requests / 60 seconds (OQ-3).]

**Consequences (testable):**
- Setting `RATE_LIMIT_REQUESTS=10 RATE_LIMIT_WINDOW_SECONDS=30` makes the 11th request within 30 s return `429`.
- Omitting both env vars reproduces the default behaviour.

---

#### FR-5: Test coverage

Every route in the test suite MUST have at least one test covering the rate-limit path (sub-limit succeeds; over-limit returns `429` with correct headers). Tests MUST use the existing `client` fixture from `tests/conftest.py`. [ASSUMPTION: the in-memory test client resets limiter state between tests — the implementation must support this (OQ-5).]

**Consequences (testable):**
- `pytest` passes with no failures after the feature is added.
- A test that fires `Limit + 1` requests asserts `429` on the last one and checks `Retry-After`.

---

## 5. Non-Goals (Explicit)

- **Per-endpoint or per-role tiers.** All routes share a single Limit in v1.
- **Distributed / multi-process state.** No Redis or external store. If the service is ever horizontally scaled, rate limiting must be revisited.
- **IP allow-listing or bypass lists.** No concept of privileged callers in v1.
- **Admin dashboard or metrics endpoint.** No observability surface for current counter values.
- **Sliding window or token-bucket algorithm.** Fixed window only; burst artefacts at window boundaries are accepted.
- **Persistence across restarts.** In-process state is ephemeral; counters reset on restart.
- **Third-party rate-limiting libraries** (`slowapi`, `limits`, etc.). Stdlib only per project guardrails.

---

## 6. MVP Scope

### 6.1 In Scope

- FastAPI middleware registered at app startup.
- Subject identification (X-User-Id → IP fallback).
- Fixed-window counter, in-process.
- `429` response with `Retry-After` header and JSON body.
- Env-var configuration with defaults.
- pytest test coverage for limit and sub-limit paths.

### 6.2 Out of Scope for MVP

- Per-route limits — deferred to v2; requires OQ-1 answered.
- Distributed state — deferred; requires horizontal-scaling decision (OQ-4).
- Proxy-header trust (`X-Forwarded-For`) — deferred; requires OQ-2 answered.
- `RateLimit-*` headers (draft RFC) — deferred; low value for internal service.

---

## 7. Success Metrics

**Primary**
- **SM-1:** `pytest` suite passes 100% with rate-limit tests included. Validates FR-2, FR-3, FR-5.

**Secondary**
- **SM-2:** A correctly throttled client retries after `Retry-After` seconds and succeeds — demonstrating the header is correct. Validates FR-3.
- **SM-3:** Env-var override changes effective limit without code change. Validates FR-4.

**Counter-metrics (do not optimize)**
- **SM-C1:** False-positive rate — legitimate clients should not be blocked. If tuning the default Limit causes operator-reported false positives, the default is wrong, not the client.

---

## 8. Open Questions

1. **OQ-1 (Architect/PM):** Should different endpoint groups have different limits (e.g., write endpoints stricter than reads)? If yes, a middleware-per-route or route-tagging approach is needed. *Blocking for v2, not v1.*

2. **OQ-2 (Ops/PM):** Is the service behind a reverse proxy that sets `X-Forwarded-For`? If yes, the IP fallback must read that header instead of the raw socket IP to avoid all traffic appearing to come from the proxy.

3. **OQ-3 (PM/Stakeholders):** Confirm default Limit and Window values. Current assumption: **60 requests / 60 seconds**. If the service handles high-frequency polling, this default will cause false positives.

4. **OQ-4 (Architect):** Is horizontal scaling (multiple processes/instances) planned? If yes, in-process state is insufficient and an external store (Redis) must be introduced. This changes the implementation significantly.

5. **OQ-5 (Engineer):** The test suite resets state between tests via the `client` fixture. The middleware must expose a reset hook or be re-instantiated per test. Confirm the chosen approach before implementation.

---

## 9. Assumptions Index

- **§1 / DL-3** — Default limit is 60 requests/60-second window.
- **§4.1 / DL-1** — Single global limit applies to all endpoints equally.
- **§FR-1 / DL-2** — `X-Forwarded-For` not in use; raw socket IP is reliable (OQ-2).
- **§FR-2 / DL-4** — In-process fixed-window state is sufficient (single instance, OQ-4).
- **§FR-4 / DL-3** — Env-var defaults are 60 / 60 (OQ-3).
- **§FR-5** — The test client supports limiter state reset between tests (OQ-5).

---

## Cross-Cutting NFRs

- **No new runtime dependencies.** Python stdlib only. Violating this requires explicit PM approval and a `pyproject.toml` change.
- **Thread safety.** The in-process counter MUST be protected by a lock; the implementation must be safe under FastAPI's default `anyio` thread-pool.
- **Latency overhead.** Middleware overhead MUST be imperceptible on the happy path (sub-millisecond dict lookup + lock acquisition).
