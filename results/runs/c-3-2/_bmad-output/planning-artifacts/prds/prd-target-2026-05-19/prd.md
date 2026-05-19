---
title: API Rate Limiting
status: draft
created: 2026-05-19
updated: 2026-05-19
---

# PRD: API Rate Limiting

## 0. Document Purpose

This PRD is for the PM, engineers, and architect responsible for the `target` FastAPI service (users + orders, SQLAlchemy + SQLite). It defines the requirements for adding rate limiting to protect the API from abuse and unintended load. Downstream: architecture design, epics and stories.

---

## 1. Vision

The `target` service currently imposes no upper bound on how frequently any caller may hit its endpoints. Any client — legitimate or malicious — can send requests at arbitrary rates, risking service degradation, data integrity issues, and unexpected infrastructure cost.

Rate limiting adds a policy layer that caps request frequency per identified client. When a client exceeds the cap the service rejects excess requests with a standard HTTP 429 response, signalling the client to back off. This makes the service predictable under load, deters casual abuse, and establishes the foundation for tiered access policies in the future.

The initial implementation targets the existing user and order routes. It must integrate cleanly with the current auth convention (`X-User-Id` header) and must not require new runtime infrastructure beyond what the service already runs.

---

## 2. Target User

### 2.1 Primary Persona

**API operator / platform maintainer.** Responsible for the health and reliability of the `target` service. Wants confidence that no single caller can saturate the service, and wants clear signals (logs, headers) when limits fire.

### 2.2 Jobs To Be Done

- Protect the service from accidental hammering by misconfigured clients.
- Deter intentional abuse or scraping.
- Give legitimate clients a clear, standard signal when they need to slow down.
- Configure limits without redeploying (stretch goal — see Open Questions).

### 2.3 Non-Users (v1)

External end-users do not interact with rate limiting directly; they receive a 429 and a `Retry-After` header. Rate limit configuration UIs or dashboards are not in scope.

### 2.4 Key User Journeys

**UJ-1. A misconfigured client is self-corrected.**
A service consumer's retry loop fires too aggressively. The rate limiter detects the burst, returns HTTP 429 with `Retry-After`, and the client backs off. The operator sees no service degradation; the misconfigured client eventually self-corrects.

**UJ-2. An operator tunes the limit.**
The operator sets the rate limit via an environment variable (or config file — see OQ-6), restarts the service, and the new limit takes effect immediately. No code change required.

---

## 3. Glossary

- **Client** — the entity whose request rate is being measured. May be identified by `X-User-Id` header value, source IP, or both. [ASSUMPTION: primary key is `X-User-Id`; IP is fallback for unauthenticated requests — see OQ-3.]
- **Rate limit** — the maximum number of requests a Client may make in a defined time window.
- **Window** — the rolling or fixed time interval over which requests are counted (e.g. 60 seconds).
- **Counter** — the per-client request count within the current window.
- **429 response** — HTTP 429 Too Many Requests; the response returned when a client exceeds its rate limit.
- **`Retry-After`** — HTTP response header indicating how many seconds the client must wait before retrying.

---

## 4. Features

### 4.1 Request Rate Enforcement

**Description:** Every inbound request is evaluated against the client's counter for the current window. If the counter is below the limit, the request proceeds and the counter is incremented. If the counter is at or above the limit, the service immediately returns HTTP 429 with a `Retry-After` header and does not execute the route handler. The feature applies to [ASSUMPTION: all authenticated routes — see OQ-2].

**Functional Requirements:**

#### FR-1: Per-client counter increment

The system increments a per-client request counter on each accepted request within the active window.

**Consequences (testable):**
- After N accepted requests in a window, the counter equals N.
- Counter resets at the start of a new window.

#### FR-2: Limit enforcement and 429 response

When a client's counter reaches or exceeds the configured limit, the system returns HTTP 429 Too Many Requests for all subsequent requests in that window.

**Consequences (testable):**
- The (limit + 1)th request in a window receives HTTP 429.
- The response body contains a machine-readable error field (e.g. `{"detail": "rate limit exceeded"}`).
- Requests below the limit receive their normal response code.

#### FR-3: `Retry-After` header

Every HTTP 429 response includes a `Retry-After` header indicating the number of seconds until the client's window resets.

**Consequences (testable):**
- HTTP 429 responses have `Retry-After: N` where N ≥ 1.
- Clients that wait `Retry-After` seconds and retry receive a non-429 response (assuming no new burst).

#### FR-4: Client identification

The system identifies the client by the `X-User-Id` request header when present. [ASSUMPTION: unauthenticated requests are identified by source IP — see OQ-3.]

**Consequences (testable):**
- Two requests with different `X-User-Id` values do not share a counter.
- Two requests with the same `X-User-Id` share a counter within the same window.

**Feature-specific NFRs:**
- Rate limit enforcement must add ≤ 5 ms median latency to any request that is not rejected. [ASSUMPTION — see OQ-7.]
- Counter storage must not require an external process (Redis, Memcached) in the initial implementation. [ASSUMPTION: in-memory per-process — see OQ-5.]

**Notes:** [NOTE FOR PM] If multi-worker deployment is required, in-memory counters will diverge across workers. OQ-5 must be resolved before architecture begins.

### 4.2 Rate Limit Configuration

**Description:** The rate limit (requests per window and window duration) is configurable without a code change. [ASSUMPTION: configuration is via environment variables — see OQ-6.]

**Functional Requirements:**

#### FR-5: Configurable limit and window

The system reads rate limit parameters (max requests, window seconds) from configuration at startup. Default values are applied when configuration is absent.

**Consequences (testable):**
- Changing the env var and restarting the service changes the enforced limit.
- With no configuration set, the service starts with a documented default (e.g. 100 req / 60 s). [ASSUMPTION on default values — see OQ-4.]

---

## 5. Non-Goals (Explicit)

- **No per-endpoint limits in v1.** A single global limit applies to all in-scope routes. Per-route or per-method tuning is deferred.
- **No per-user tiers.** All clients share the same limit. Paid/free tiering is out of scope.
- **No distributed counter store.** Redis or equivalent shared cache is not introduced in v1. In-memory only.
- **No rate limit admin UI or API.** Operators configure via env vars / config; there is no management endpoint.
- **No IP allowlist / denylist.** Bypassing rate limiting for trusted IPs is out of scope.
- **No request body inspection.** Limits apply to request count, not payload size or content.
- **No alerting or metrics pipeline.** Logging a 429 event is acceptable; wiring to Prometheus, Datadog, or similar is out of scope.

---

## 6. MVP Scope

### 6.1 In Scope

- In-process rate limit middleware/dependency integrated into the FastAPI service.
- Per-client counters keyed on `X-User-Id` (fallback: source IP). [ASSUMPTION — OQ-3]
- Configurable limit and window via environment variable.
- HTTP 429 response with `Retry-After` header.
- Unit and integration tests using the existing `client` fixture in `tests/conftest.py`.

### 6.2 Out of Scope for MVP

- Distributed counter storage (Redis) — deferred to v2 if multi-worker deployment is required.
- Per-endpoint or per-user-tier limits — deferred to v2.
- Runtime reconfiguration without restart — deferred; env-var config requires restart.
- Metrics/alerting integration — deferred.
- Admin API — deferred.

---

## 7. Success Metrics

**Primary**
- **SM-1:** 100% of requests exceeding the configured limit receive HTTP 429. Validates FR-2.
- **SM-2:** All HTTP 429 responses include a valid `Retry-After` header. Validates FR-3.

**Secondary**
- **SM-3:** Median added latency for non-rejected requests ≤ 5 ms under load. Validates FR-1 NFR.
- **SM-4:** Rate limit parameters change takes effect within one service restart, with no code change. Validates FR-5.

**Counter-metrics (do not optimize)**
- **SM-C1:** False-positive rate (legitimate requests rejected). Should remain 0% under normal traffic patterns. Counterbalances SM-1 — do not tighten limits to the point of rejecting valid clients.

---

## 8. Open Questions

1. **OQ-1: Why now?** Is this driven by a specific incident, security audit, compliance requirement, or proactive hardening? Answer affects urgency and scope.
2. **OQ-2: Which endpoints?** Should rate limiting apply to all routes, or only specific ones (e.g. order creation, user registration)? Determines implementation scope.
3. **OQ-3: Client identification key.** Primary key: `X-User-Id`? Fallback for unauthenticated requests: source IP? Both? Neither (global per-service limit only)?
4. **OQ-4: Default limit values.** What is the target limit? (e.g. 100 req / 60 s per client.) Who owns this number?
5. **OQ-5: Counter storage for multi-worker.** Is the service currently run as a single process? If multiple workers are expected, in-memory counters are insufficient and a shared store (Redis) or sticky routing is required.
6. **OQ-6: Configuration mechanism.** Environment variables acceptable? Or is a config file / secrets manager preferred?
7. **OQ-7: Latency budget.** Is ≤ 5 ms added overhead an acceptable constraint, or does the service have a tighter SLA?

---

## 9. Assumptions Index

- **§3 / FR-4:** Primary client key is `X-User-Id`; unauthenticated requests fall back to source IP.
- **§4.1:** Rate limiting applies to all authenticated routes (not a subset).
- **§4.1 NFR:** ≤ 5 ms median overhead is the acceptable latency budget.
- **§4.1 NFR:** In-memory counter storage only; no external process required.
- **§4.2 / FR-5:** Configuration via environment variables.
- **§4.2 / FR-5:** Default limit is 100 requests per 60-second window.
