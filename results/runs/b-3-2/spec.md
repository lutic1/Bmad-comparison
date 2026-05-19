# Feature Specification: API Rate Limiting

**Feature Branch**: `001-api-rate-limiting`

**Created**: 2026-05-19

**Status**: Draft

**Input**: User description: "Add rate limiting to the API."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Request Throttling Enforcement (Priority: P1)

As an API client, when I exceed the allowed number of requests within a time window,
I receive a clear error response telling me I have been throttled, so I know to
slow down rather than continue hammering the service.

**Why this priority**: Core protection against abuse and overload. Without this,
rate limiting delivers no value.

**Independent Test**: Send more requests than the configured limit within a single
time window and verify that requests beyond the limit are rejected with a
distinct, recognizable error response.

**Acceptance Scenarios**:

1. **Given** a client has not exceeded the rate limit, **When** they send a
   request, **Then** the request succeeds normally with no degradation.
2. **Given** a client has exhausted their request quota for the current window,
   **When** they send an additional request, **Then** the service responds with
   a "Too Many Requests" error and does not process the request.
3. **Given** a client was previously throttled and the time window has reset,
   **When** they send a new request, **Then** the request succeeds normally.

---

### User Story 2 - Rate Limit Status Visibility (Priority: P2)

As an API client, I can see my current rate limit quota and how much remains in
every response, so I can manage my request pace proactively without waiting to
hit the limit.

**Why this priority**: Without visibility, clients have no way to self-regulate,
leading to unavoidable throttling and degraded integrations.

**Independent Test**: Issue a request within the allowed limit and verify the
response includes fields describing the total quota, how many requests remain,
and when the quota resets.

**Acceptance Scenarios**:

1. **Given** a client sends any API request, **When** the response is returned,
   **Then** it includes the total request limit, the remaining requests, and the
   time at which the quota resets.
2. **Given** a client has been throttled, **When** the error response is
   returned, **Then** it includes the time the client must wait before retrying.

---

### User Story 3 - Per-Client Isolation (Priority: P3)

As a well-behaved API client, my request quota is independent of other clients'
usage, so that a misbehaving or high-volume client does not consume my quota or
degrade my experience.

**Why this priority**: Without isolation, one client can exhaust a shared pool
and deny service to others.

**Independent Test**: Exhaust the quota for one client identity, then send a
request from a different client identity and verify it succeeds normally.

**Acceptance Scenarios**:

1. **Given** Client A has exceeded their rate limit, **When** Client B sends a
   request, **Then** Client B's request succeeds (assuming B is within their own
   quota).
2. **Given** an authenticated client (identified by user identity) and an
   unauthenticated client sharing the same network address, **When** either
   client is throttled, **Then** only that client's requests are rejected.

---

### Edge Cases

- What happens to in-flight requests when the quota is exhausted mid-burst?
- How is a client identified when no user identity and no network address is
  reliably available?
- What response does a client receive if the rate-limit tracking store is
  temporarily unavailable?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The service MUST reject requests from a client that exceeds the
  configured request quota within the active time window with a "Too Many
  Requests" response.
- **FR-002**: Every API response MUST include the client's total quota, remaining
  quota, and quota reset time.
- **FR-003**: Throttled responses MUST include the time the client must wait
  before the next request will be accepted.
- **FR-004**: The service MUST track request counts independently per client
  identity; one client's usage MUST NOT affect another client's quota.
- **FR-005**: Authenticated clients MUST be identified by their declared user
  identity; unauthenticated clients MUST be identified by their network address.
- **FR-006**: The rate limit quota and time window MUST be configurable without
  code changes.
- **FR-007**: When the quota resets at the end of a time window, the client's
  counter MUST be reset and requests MUST succeed again up to the full quota.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Clients that exceed the configured limit receive a "Too Many
  Requests" response 100% of the time, with no excess requests processed.
- **SC-002**: All API responses include complete rate limit status information,
  verified across all endpoints.
- **SC-003**: Exhausting one client's quota has zero impact on a different
  client's ability to make requests.
- **SC-004**: After a quota window resets, previously throttled clients can
  immediately resume making requests up to the full quota.
- **SC-005**: The service remains fully functional for compliant clients even
  while actively throttling other clients.

## Assumptions

- Rate limiting applies uniformly to all API endpoints (no per-endpoint
  differentiation in this iteration).
- Client state (request counts) is held in-memory; it does not need to survive
  service restarts.
- A reasonable default quota (e.g., 60 requests per minute) is acceptable and
  can be adjusted via configuration.
- Unauthenticated client identity is derived from the request's originating
  network address.
- Mobile clients behind shared network addresses (NAT) are acceptable edge-case
  casualties; the priority is protecting identified users.
