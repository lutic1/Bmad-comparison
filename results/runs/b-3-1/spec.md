# Feature Specification: API Rate Limiting

**Feature Branch**: `001-api-rate-limiting`

**Created**: 2026-05-18

**Status**: Draft

**Input**: User description: "Add rate limiting to the API."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Excess Requests Rejected (Priority: P1)

A client that sends more requests than the allowed limit within a time window receives a clear rejection response instead of being served. This protects the service from being overwhelmed by any single client and ensures fair resource availability for all callers.

**Why this priority**: Core safety guarantee — without this, rate limiting delivers no value. All other stories depend on enforcement being in place.

**Independent Test**: Send requests beyond the configured limit from a single client and verify rejections are returned while other clients continue to be served normally.

**Acceptance Scenarios**:

1. **Given** a client has already made the maximum allowed requests in the current window, **When** the client makes one more request, **Then** the system responds with a 429 Too Many Requests status and does not process the request.
2. **Given** a client has been rate limited, **When** the time window resets, **Then** the client can successfully make requests again up to the limit.
3. **Given** client A has exhausted its limit, **When** client B (a different identity) makes a request, **Then** client B is served normally without being affected by client A's usage.

---

### User Story 2 - Rate Limit Transparency via Headers (Priority: P2)

Every API response includes headers that tell the caller how many requests they have remaining in the current window and when their quota will reset. This lets well-behaved clients self-regulate and avoid hitting the limit unexpectedly.

**Why this priority**: Without visibility into quota status, clients cannot adapt their behavior; this significantly reduces the usability of rate limiting for legitimate high-volume callers.

**Independent Test**: Make any request to the API and confirm the response includes accurate rate limit headers reflecting current usage and reset time.

**Acceptance Scenarios**:

1. **Given** a client makes a request within their quota, **When** the response is returned, **Then** it includes headers for the total limit, remaining requests, and the time until the window resets.
2. **Given** a client is rate limited (429 response), **When** the response is received, **Then** it includes a header or body field indicating when the client may retry.
3. **Given** a client makes sequential requests, **When** each response is inspected, **Then** the remaining-requests header decrements correctly with each call.

---

### Edge Cases

- What happens when a client sends requests exactly at the limit boundary (the N-th request vs. N+1-th)?
- How does the system handle requests that arrive simultaneously from the same client at the window boundary?
- What happens when a request arrives with no client identifier?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST track the number of requests made by each client within a rolling or fixed time window.
- **FR-002**: System MUST reject any request that exceeds the allowed limit within the current window with an HTTP 429 Too Many Requests response.
- **FR-003**: System MUST apply rate limit counters independently per client so that one client's usage has no effect on other clients' quotas.
- **FR-004**: System MUST reset a client's request count at the start of each new time window.
- **FR-005**: System MUST include rate limit status headers in every API response (total limit, remaining requests, and window reset time).
- **FR-006**: System MUST include retry guidance in every 429 response indicating when the client may make requests again.
- **FR-007**: System MUST apply rate limiting uniformly across all API endpoints.

### Key Entities

- **Rate Limit Rule**: Defines the maximum number of requests allowed and the duration of the time window (e.g., 100 requests per 60 seconds). Applied globally to all endpoints.
- **Client Request Record**: Tracks the request count and window start time for an individual client, identified by the client's unique identity. Resets automatically when the window expires.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Clients that exceed the request limit receive a rejection response; 100% of over-limit requests are blocked with no successful processing.
- **SC-002**: Clients that remain within their quota experience no degradation — response behavior is identical to pre-rate-limiting for allowed requests.
- **SC-003**: Rate limit counters are fully isolated per client — exhausting one client's quota has zero impact on any other client's available requests.
- **SC-004**: Every API response carries accurate rate limit headers; header values reflect the true remaining quota and correct reset time at the moment of the response.
- **SC-005**: Rate-limited clients can determine exactly when to retry without needing to make additional requests to discover their status.

## Assumptions

- Rate limiting is applied per authenticated user, identified by the `X-User-Id` header already used for authentication in this service.
- Requests with no client identifier are rejected before reaching rate limit evaluation (existing auth enforcement covers this).
- The default limit is 100 requests per 60-second window; this is configurable at the service level but not per individual client.
- Rate limit state is stored in-memory and does not need to survive server restarts; the service operates as a single instance.
- All API endpoints are subject to the same rate limit rule; per-endpoint granularity is out of scope for this iteration.
