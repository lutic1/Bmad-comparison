# Feature Specification: API Rate Limiting

**Feature Branch**: `001-api-rate-limiting`

**Created**: 2026-05-19

**Status**: Draft

**Input**: User description: "Add rate limiting to the API."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Client Blocked When Quota Exceeded (Priority: P1)

A client that sends requests too frequently within a time window receives a clear
rejection response telling them they have been rate-limited and when they may retry.

**Why this priority**: Enforcement is the core value of rate limiting. Without it
the feature does not exist.

**Independent Test**: Send requests beyond the configured limit and verify a
rejection response with a retry signal is returned — no further requests from that
scope are served until the window resets.

**Acceptance Scenarios**:

1. **Given** a client has consumed their full request quota for the current window,
   **When** they send one additional request,
   **Then** the system rejects it with a rate-limit error and indicates when the
   client may retry.

2. **Given** a client is rate-limited,
   **When** the time window resets,
   **Then** the client's next request is accepted normally.

3. **Given** a client is rate-limited,
   **When** they inspect the rejection response,
   **Then** the response clearly identifies the reason as rate limiting and includes
   a retry signal.

---

### User Story 2 - Client Can Monitor Remaining Quota (Priority: P2)

Every API response includes rate limit status so clients can proactively manage
their request cadence and avoid hitting the limit unexpectedly.

**Why this priority**: Visibility prevents disruption for well-behaved clients and
is required for any production integration.

**Independent Test**: Make a single request within quota and verify the response
carries the allowed limit, how many requests remain, and when the window resets.

**Acceptance Scenarios**:

1. **Given** a client makes any API request within their quota,
   **When** the response is received,
   **Then** it includes the total allowed requests per window, the remaining requests
   in the current window, and the time at which the window resets.

2. **Given** a client has used exactly half their quota,
   **When** they inspect the response,
   **Then** the remaining count reflects their actual usage so far.

---

### Edge Cases

- What happens when two requests arrive simultaneously and together would exceed the limit?
- How does the system handle clients with no identifiable scope (no user header, no IP)?
- What happens if the request count store is temporarily unavailable?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST reject requests that exceed the configured rate limit for
  the client's scope and return a response indicating the client is rate-limited.
- **FR-002**: System MUST include a retry signal in rate-limit rejection responses
  so clients know when they may resume requests.
- **FR-003**: System MUST attach rate limit status (limit, remaining, reset time) to
  every API response, including both accepted and rejected requests.
- **FR-004**: System MUST apply rate limiting consistently across all API endpoints.
- **FR-005**: System MUST scope rate limits per authenticated user when a user
  identity is present, and fall back to the client's network address otherwise.
- **FR-006**: System MUST enforce limits within a fixed sliding or tumbling time
  window of 60 seconds, allowing 100 requests per window per scope by default.

### Key Entities

- **Rate Limit Scope**: The identity against which requests are counted (user ID or
  IP address).
- **Request Window**: The fixed time interval (60 seconds by default) over which
  requests are counted and the quota is enforced.
- **Quota**: The maximum number of requests allowed per scope per window (100 by
  default).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Clients that exceed their quota receive a rate-limit rejection
  response within the same response time as a normal request (no added latency for
  the enforcement check itself).
- **SC-002**: 100% of API responses include rate limit status information.
- **SC-003**: Rate limiting applies uniformly — no endpoint is exempt.
- **SC-004**: After a window reset, a previously rate-limited client can immediately
  resume requests without manual intervention.
- **SC-005**: Zero legitimate requests (within quota) are incorrectly rejected under
  normal operating conditions.

## Assumptions

- Authenticated clients are identified by the existing user identity header already
  present in the API; no new authentication mechanism is introduced.
- The default quota (100 requests per 60-second window) is sufficient for initial
  deployment; the values are configuration, not hard-coded business logic.
- All API endpoints are subject to the same rate limit policy; per-endpoint
  differentiation is out of scope for this feature.
- The retry signal communicated to clients is a point in time (seconds until reset),
  not a guaranteed reservation of capacity.
- Persistence of request counts does not need to survive a service restart; in-memory
  tracking is acceptable for this initial implementation.
