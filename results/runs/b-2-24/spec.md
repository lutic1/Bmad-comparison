# Feature Specification: Order Refund

**Feature Branch**: `001-order-refund`

**Created**: 2026-05-19

**Status**: Draft

**Input**: User description: "Add a `POST /orders/{order_id}/refund` endpoint. It should: require authentication, validate the order exists and belongs to the requesting user, only allow refunds within 30 days of order creation, mark the order as refunded (add a field if needed), and return the refund record. Include tests."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Successful Refund Request (Priority: P1)

An authenticated user requests a refund for one of their orders that was placed within the last 30 days. The system marks the order as refunded and returns the refund details.

**Why this priority**: Core happy path — without this, the feature delivers no value.

**Independent Test**: Can be fully tested by submitting a refund request for a recent eligible order and verifying the returned refund record and the updated order state.

**Acceptance Scenarios**:

1. **Given** an authenticated user with an order placed within the last 30 days, **When** they request a refund for that order, **Then** the system returns a refund record with the refund timestamp and the order is marked as refunded.
2. **Given** an authenticated user submits a second refund request for an already-refunded order, **When** the request is processed, **Then** the system rejects it with a clear error indicating the order has already been refunded.

---

### User Story 2 - Refund Rejected: Ownership Violation (Priority: P2)

An authenticated user attempts to refund an order that belongs to a different user. The system rejects the request without revealing whether the order exists.

**Why this priority**: Security requirement — prevents users from refunding other users' orders.

**Independent Test**: Submit a refund request for an order owned by a different user and confirm the system returns an appropriate error.

**Acceptance Scenarios**:

1. **Given** an authenticated user, **When** they request a refund for an order that does not belong to them, **Then** the system responds with a not-found or forbidden error without disclosing the order's existence.

---

### User Story 3 - Refund Rejected: Expired Window (Priority: P3)

An authenticated user attempts to refund an order that was placed more than 30 days ago. The system rejects the request with a clear explanation.

**Why this priority**: Enforces the 30-day refund policy constraint.

**Independent Test**: Submit a refund request for an order created 31+ days ago and confirm rejection with an appropriate message.

**Acceptance Scenarios**:

1. **Given** an authenticated user with an order created more than 30 days ago, **When** they request a refund, **Then** the system rejects the request with an error indicating the refund window has expired.
2. **Given** an order created exactly 30 days ago, **When** the user requests a refund, **Then** the system accepts the request (boundary inclusive).

---

### Edge Cases

- What happens when the order ID does not exist at all? → Not-found error, no information leaked.
- What happens when the user is not authenticated? → Request is rejected before any order lookup.
- What happens when the same order is refunded concurrently by two simultaneous requests? → Only one succeeds; the second receives an already-refunded error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The refund endpoint MUST require a valid authenticated user identity; unauthenticated requests MUST be rejected.
- **FR-002**: The system MUST verify that the specified order exists and is owned by the requesting user; orders belonging to other users MUST be treated as not found.
- **FR-003**: The system MUST reject refund requests for orders created more than 30 days before the request time.
- **FR-004**: The system MUST reject refund requests for orders that have already been refunded.
- **FR-005**: Upon a successful refund request, the system MUST persistently mark the order as refunded (recording the refund timestamp).
- **FR-006**: The system MUST return a refund record containing at minimum: the order identifier, the refund timestamp, and confirmation of the refunded status.
- **FR-007**: Tests MUST cover: the happy path, already-refunded rejection, expired-window rejection, ownership violation, and unauthenticated access.

### Key Entities

- **Order**: Represents a purchase. Gains a `refunded` boolean and a `refunded_at` timestamp field to record refund state.
- **Refund Record**: The response payload returned on a successful refund, derived from the updated order. Contains: order ID, refund timestamp, refunded status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An eligible refund request completes and returns a refund record in a single interaction with no additional steps required from the user.
- **SC-002**: Refund requests for orders older than 30 days are rejected 100% of the time with a human-readable error.
- **SC-003**: Refund requests for orders owned by other users are rejected 100% of the time without disclosing order ownership.
- **SC-004**: Refund requests for already-refunded orders are rejected 100% of the time.
- **SC-005**: All seven specified test scenarios (FR-007) pass with no test failures.

## Assumptions

- The existing authentication mechanism (`X-User-Id` header) is sufficient for identifying the requesting user; no new auth scheme is needed.
- "30 days" means a calendar duration of 30 days measured from the order's creation timestamp to the moment the refund request is received.
- The 30-day boundary is inclusive (an order created exactly 30 days ago is still eligible).
- A refund is a state change on the order record; no separate payment-processor integration is in scope.
- Only one refund per order is permitted; partial refunds are out of scope.
- The refund record returned is derived from the order; no separate `Refund` database table is required unless the implementer determines one is necessary.
