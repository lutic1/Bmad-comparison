# Feature Specification: Order Refund

**Feature Branch**: `001-order-refund`

**Created**: 2026-05-19

**Status**: Draft

**Input**: User description: "Add a `POST /orders/{order_id}/refund` endpoint. It should require authentication, validate the order exists and belongs to the requesting user, only allow refunds within 30 days of order creation, mark the order as refunded (add a field if needed), and return the refund record. Include tests."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Successful Refund Request (Priority: P1)

An authenticated user who placed an order within the last 30 days submits a refund
request. The system validates their identity and order ownership, records the refund,
and returns a confirmation record.

**Why this priority**: Core happy path — the primary value delivered by this feature.

**Independent Test**: Can be tested by submitting a valid refund request and verifying
the refund record is returned and the order is marked as refunded.

**Acceptance Scenarios**:

1. **Given** an authenticated user with an order they own that was created within
   the last 30 days, **When** they request a refund, **Then** the system returns
   a refund record and the order is marked as refunded.
2. **Given** an authenticated user with an order created exactly on the 30-day
   boundary, **When** they request a refund, **Then** the refund is accepted
   (boundary is inclusive).

---

### User Story 2 - Refund Rejection on Invalid Conditions (Priority: P2)

An authenticated user attempts a refund that cannot be processed — because the order
does not exist, belongs to a different user, is outside the 30-day window, or has
already been refunded. The system rejects the request with a clear, informative
response.

**Why this priority**: Prevents data corruption and unauthorized actions; required
for correctness and security.

**Independent Test**: Can be tested by submitting refund requests under each invalid
condition and verifying each is rejected with an appropriate error response.

**Acceptance Scenarios**:

1. **Given** an authenticated user, **When** they request a refund for an order ID
   that does not exist, **Then** the system returns a "not found" error.
2. **Given** an authenticated user, **When** they request a refund for an order that
   belongs to a different user, **Then** the system returns a "not found" error
   (order ownership must not be disclosed to unauthorized users).
3. **Given** an authenticated user, **When** they request a refund for an order
   created more than 30 days ago, **Then** the system returns a rejection error
   explaining the refund window has expired.
4. **Given** an authenticated user, **When** they request a refund for an order that
   has already been refunded, **Then** the system returns a rejection error indicating
   the order is already refunded.

---

### User Story 3 - Unauthenticated Refund Attempt (Priority: P3)

A request to refund an order is made without valid authentication credentials.
The system rejects the request before performing any order lookup.

**Why this priority**: Security gate — must work correctly but is straightforward
to implement given existing authentication infrastructure.

**Independent Test**: Can be tested by submitting a refund request without
authentication credentials and verifying a rejection response is returned.

**Acceptance Scenarios**:

1. **Given** a request with no authentication credentials, **When** a refund is
   requested for any order, **Then** the system returns an "unauthorized" error
   without revealing order details.

---

### Edge Cases

- What happens when the order creation timestamp is exactly 30 days ago (inclusive boundary)?
- How does the system handle an already-refunded order — idempotent acceptance or explicit rejection?
- What is returned in the refund record if the order has no monetary amount stored?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST require valid user authentication before processing any refund request.
- **FR-002**: System MUST verify that the specified order exists.
- **FR-003**: System MUST verify that the order belongs to the authenticated user; orders owned
  by other users MUST be treated as not found (no ownership disclosure).
- **FR-004**: System MUST reject refund requests for orders created more than 30 days before
  the request timestamp.
- **FR-005**: System MUST reject refund requests for orders that have already been refunded.
- **FR-006**: System MUST record the refunded status on the order when a refund is successfully
  processed (adding a field to the order record if not already present).
- **FR-007**: System MUST return a refund record on successful processing, containing at minimum:
  order identifier, refund status, and the timestamp at which the refund was recorded.
- **FR-008**: The feature MUST ship with automated tests covering: the successful refund flow,
  each rejection scenario (unauthenticated, not found, wrong owner, expired window, already
  refunded).

### Key Entities

- **Order**: Represents a placed order. Relevant attributes: unique identifier, owning user,
  creation timestamp, refund status (boolean), and refund timestamp (nullable).
- **Refund Record**: The response artifact confirming a processed refund. Contains: order
  identifier, refunded status (true), and the refund timestamp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Eligible refund requests (authenticated, owned, within 30 days, not yet refunded)
  are accepted and recorded 100% of the time.
- **SC-002**: Ineligible refund requests are rejected 100% of the time with a response that
  identifies the reason (expired window, already refunded) or withholds it for security
  (unauthenticated, wrong owner).
- **SC-003**: No refund operation exposes order data belonging to a user other than the
  requester.
- **SC-004**: Automated test suite covers all acceptance scenarios defined in User Stories
  1–3, with each scenario independently verifiable.

## Assumptions

- An order can only be refunded once; the refund operation is not idempotent — a second
  request on an already-refunded order is an error.
- The 30-day window is calculated from the order's creation timestamp to the moment the
  refund request is received (wall-clock time, UTC).
- User identity is established by the existing authentication mechanism already in use
  across the service; this feature reuses it without modification.
- The refund record does not require a separate persistent entity — it is derived from
  the updated order record and returned in the response.
- Monetary amount and payment provider details are out of scope; this feature marks
  the order status only and does not integrate with a payment processor.
