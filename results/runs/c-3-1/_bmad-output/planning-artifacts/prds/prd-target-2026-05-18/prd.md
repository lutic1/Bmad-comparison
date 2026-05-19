---
title: API Rate Limiting
status: draft
created: 2026-05-18
updated: 2026-05-18
---

# PRD: API Rate Limiting

## 0. Document Purpose

This PRD is for the PM, architect, and downstream story authors. It defines requirements for adding rate limiting to the FastAPI users-and-orders service. Vocabulary is anchored in §3 Glossary. Functional requirements are grouped by feature with globally stable FR-IDs. Assumptions are tagged `[ASSUMPTION]` and indexed in §9. Open questions that block safe architecture or implementation are enumerated in §8.

---

## 1. Vision

The users-and-orders service currently has no mechanism to prevent a single client from monopolising API capacity — whether through a buggy retry loop, a misconfigured integration, or deliberate abuse. Without rate limiting, one bad actor can degrade the service for every other caller and give operators no early signal before things break.

Rate limiting adds a lightweight contract between callers and the service: each client gets a fair allocation of requests per window, and exceeds it at the cost of a clear, retryable error. The feature is transparent to well-behaved clients, adds no latency on the happy path, and gives operators a concrete knob to tune as usage patterns mature.

The v1 target is an in-process, in-memory implementation that fits the service's current single-instance deployment model and adds no new infrastructure dependencies.

---

## 2. Target User

### 2.1 Primary Persona

**API operator** — the engineer or team responsible for running the service. They need confidence that a single misbehaving client cannot take down or meaningfully degrade the service for other callers.

### 2.2 Jobs To Be Done

- Know that the service is protected from accidental and deliberate request floods.
- Configure limits without touching application code (environment variables or config).
- Observe when limits are being hit so they can tune or investigate.

### 2.3 Non-Users (v1)

- End-users or API consumers: they experience the 429 response but are not the intended audience for configuration or observability.
- Distributed/multi-instance operators: v1 targets single-instance deployments only.

### 2.4 Key User Journeys

**UJ-1. A buggy client hammers the orders endpoint.**
A service integration sends a retry loop with no backoff and fires 600 POST /orders requests in a minute. The rate limiter kicks in after the window threshold is exceeded, returns `429 Too Many Requests` with a `Retry-After` header for each subsequent request in that window, and the service remains healthy for all other callers. The next window resets and the client resumes normally if fixed.

**UJ-2. An operator tunes limits for a new traffic pattern.**
Traffic analysis shows the default 60 req/min is too tight for a batch job that legitimately sends 200 requests/min. The operator raises the relevant limit via environment variable and restarts the service. No code change required.

---

## 3. Glossary

- **Rate limit** — a cap on the number of requests a single **client identity** may make within a **window**.
- **Client identity** — the key used to bucket requests for counting. For unauthenticated endpoints: the caller's IP address. For authenticated endpoints: the `X-User-Id` header value. [ASSUMPTION: dual-key strategy — see OQ-2]
- **Window** — the rolling or fixed time period over which requests are counted (e.g. 60 seconds).
- **Limit threshold** — the maximum number of requests allowed per client identity per window.
- **429 response** — an HTTP `429 Too Many Requests` response, including a `Retry-After` header indicating when the client may retry.
- **Authenticated endpoint** — an endpoint that requires a valid `X-User-Id` header (`POST /orders`, `GET /orders/{order_id}`).
- **Unauthenticated endpoint** — an endpoint with no auth requirement (`GET /health`, `POST /users`, `GET /users/{user_id}`).
- **In-memory store** — rate limit counters held in the running process; reset on restart; sufficient for single-instance deployment.

---

## 4. Features

### 4.1 Request Rate Enforcement

**Description:** Every inbound request is evaluated against the rate limit for its client identity and endpoint group before being processed. Requests within the limit pass through with no added latency. Requests that exceed the limit are rejected immediately with a `429 Too Many Requests` response. The feature is implemented as FastAPI middleware or a dependency so it applies uniformly without per-route changes. Realizes UJ-1, UJ-2.

[ASSUMPTION: middleware approach preferred over per-route dependency to avoid per-endpoint boilerplate — see OQ-5]

**Functional Requirements:**

#### FR-1: Enforce per-identity rate limit

The system SHALL count requests per **client identity** within a rolling **window** and reject requests that exceed the configured **limit threshold**.

**Consequences (testable):**
- A client that sends N requests within one window, where N ≤ threshold, receives `2xx` responses for all N requests.
- A client that sends N+1 requests within one window, where N equals the threshold, receives `429` for request N+1 and all subsequent requests in that window.
- After the window resets, the same client may send up to threshold requests again before being limited.

#### FR-2: Identity keying

For **unauthenticated endpoints**, the **client identity** SHALL be the request's source IP address.
For **authenticated endpoints**, the **client identity** SHALL be the `X-User-Id` header value.

[ASSUMPTION: if `X-User-Id` is absent on an authenticated endpoint, the request will already be rejected `401` before the rate limiter evaluates it — no special handling needed]

**Consequences (testable):**
- Two different IP addresses each making threshold requests in the same window are each independently limited, not combined.
- Two requests carrying different `X-User-Id` values are tracked separately.
- A single `X-User-Id` value making requests from two different IPs counts as one identity (not two).

**Out of Scope:**
- Per-endpoint custom limits in v1. [NON-GOAL for MVP] All endpoints share the same threshold within their group (authenticated vs. unauthenticated). [ASSUMPTION — see OQ-1]

#### FR-3: 429 response shape

When a request is rejected, the system SHALL respond with:
- HTTP status `429 Too Many Requests`
- `Retry-After` header set to the number of seconds until the current window resets
- JSON body: `{"detail": "Rate limit exceeded. Retry after {N} seconds."}`

**Consequences (testable):**
- Rejected response status is exactly `429`.
- `Retry-After` header is present and is a positive integer.
- Response body is valid JSON with a `detail` field.

#### FR-4: Health endpoint exemption

`GET /health` SHALL be exempt from rate limiting. [ASSUMPTION — see OQ-1]

**Consequences (testable):**
- Sending 10× the threshold requests to `GET /health` in one window returns `200` for all of them.

**Feature-specific NFRs:**
- The rate limiter SHALL add no measurable latency (< 1 ms p99) on the non-limited (pass-through) path.
- The rate limiter SHALL NOT raise an unhandled exception when the in-memory store is under concurrent load; it must fail open (allow the request) rather than return `500`. [ASSUMPTION — see OQ-4]

---

### 4.2 Operator Configuration

**Description:** Limit thresholds and window duration are configurable via environment variables at startup, with sensible defaults. No code changes are required to adjust limits. Realizes UJ-2.

**Functional Requirements:**

#### FR-5: Environment-variable configuration

The system SHALL read the following environment variables at startup:

| Variable | Default | Description |
|---|---|---|
| `RATE_LIMIT_REQUESTS` | `60` | Max requests per window per client identity |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Window duration in seconds |

**Consequences (testable):**
- Service started with `RATE_LIMIT_REQUESTS=10` enforces a limit of 10, not 60.
- Service started without any env vars enforces the defaults above.

---

## 5. Non-Goals (Explicit)

- **DDoS / volumetric attack mitigation** — this is an application-layer guard, not a network-layer defense. Infrastructure-level protection (CDN, WAF, load balancer) is out of scope.
- **Per-endpoint custom limits** — v1 applies uniform limits within endpoint groups. Fine-grained per-route configuration is deferred.
- **Distributed rate limiting** — v1 state is in-memory and per-process. Multi-instance coordination (via Redis or similar) is not a v1 requirement.
- **IP allowlisting / bypasslisting** — no mechanism to exempt specific IPs or users from limits in v1.
- **Rate limit observability / metrics** — no counters, dashboards, or log lines for how often limits are hit. [NOTE FOR PM: this is a likely v2 ask once operators see 429s in logs]
- **Authenticated user limits different from anonymous limits** — v1 uses one global threshold; if the team needs separate limits per user tier, that is a future feature.
- **Persistent rate limit state across restarts** — in-memory counters reset on process restart; this is acceptable for v1.

---

## 6. MVP Scope

### 6.1 In Scope

- In-process, in-memory rate limit counter (sliding or fixed window — architect's choice).
- Dual identity key: IP for unauthenticated endpoints, `X-User-Id` for authenticated.
- Universal enforcement on all endpoints except `GET /health`.
- `429` response with `Retry-After` header and JSON body.
- Environment-variable configuration with documented defaults.
- Unit and integration tests covering: pass-through, threshold breach, window reset, 429 shape, health exemption, env-var override.

### 6.2 Out of Scope for MVP

- Redis or external store (deferred to v2 when multi-instance is needed).
- Per-endpoint limits (deferred; one threshold covers all).
- Observability hooks — metrics, structured log lines for 429 events (v2).
- IP allowlist / bypasslist (v2 if needed).
- Async-safe distributed coordination (v2).

---

## 7. Success Metrics

**Primary**
- **SM-1**: Zero unhandled exceptions attributable to the rate limiter under normal load. Validates FR-1, FR-3. Measured by absence of `500` errors in service logs after deploy.
- **SM-2**: All rate-limit-related test cases pass (pass-through, breach, reset, 429 shape, health exemption, env-var override). Validates FR-1 through FR-5.

**Secondary**
- **SM-3**: p99 latency on non-limited requests increases by < 1 ms after the feature is deployed. Validates FR-1 NFR.

**Counter-metrics (do not optimise)**
- **SM-C1**: Do not optimise for minimising 429 responses. A low 429 rate may mean limits are too loose, not that the feature is working well.

---

## 8. Open Questions

1. **OQ-1 — Scope:** Should `GET /health` be exempt and should all other endpoints share one threshold, or should authenticated and unauthenticated endpoints have separate configurable limits?
   *Blocker for architect if separate limits are required — impacts the configuration schema.*

2. **OQ-2 — Identity key:** Is the dual-key strategy (IP for anon, `X-User-Id` for auth) correct, or should authenticated endpoints also fall back to IP if the header is absent for some reason?
   *Current assumption: absent `X-User-Id` on an auth endpoint → `401` before rate limiter fires. Confirm.*

3. **OQ-3 — Thresholds:** Are the proposed defaults (60 req/min) acceptable? Are there known clients or batch jobs that would be impacted?
   *Non-blocker for architecture but should be resolved before first deploy.*

4. **OQ-4 — Failure mode:** Should the rate limiter fail open (allow request) or fail closed (deny request / return 500) if the in-memory counter throws an unexpected error?
   *Current assumption: fail open. Confirm with operator.*

5. **OQ-5 — Implementation approach:** Middleware vs. FastAPI dependency for enforcement. Middleware is cleaner for universal enforcement; a dependency allows per-route opt-in/opt-out. Architect to decide based on exemption requirements.

6. **OQ-6 — New dependency:** Is adding `slowapi` (wraps `limits` library) acceptable, or must the implementation use stdlib only?
   *CLAUDE.md requires clear justification for new deps. Stdlib sliding window is feasible but more code; `slowapi` is battle-tested and minimal. Architect to weigh in.*

---

## 9. Assumptions Index

- **§3 / FR-2** — Dual-key strategy: IP for unauthenticated, `X-User-Id` for authenticated. (OQ-2)
- **§4.1** — Middleware approach preferred over per-route dependency. (OQ-5)
- **§FR-2** — Missing `X-User-Id` on an authenticated endpoint results in `401` before rate limiter fires; no special handling needed in the limiter.
- **§FR-4** — `GET /health` is exempt from rate limiting. (OQ-1)
- **§4.1 NFR** — Rate limiter fails open (allows request) on unexpected internal error rather than returning `500`. (OQ-4)
- **§FR-1 Out of Scope** — All endpoints (except `/health`) share a single threshold in v1; no per-endpoint custom limits. (OQ-1)
