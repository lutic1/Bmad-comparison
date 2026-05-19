# Feature Specification: Order Refund

**Feature Branch**: `001-order-refund`

**Created**: 2026-05-18

**Status**: Draft

**Input**: User description: "Add a `POST /orders/{order_id}/refund` endpoint. It should: require authentication, validate the order exists and belongs to the requesting user, only allow refunds within 30 days of order creation, mark the order as refunded (add a field if needed), and return the refund record. Include tests."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Request a Refund (Priority: P1)

An authenticated user submits a refund request for one of their own orders. The order was placed within the last 30 days and has not previously been refunded. The system marks the order as refunded and returns the refund record.

**Why this priority**: This is the entire feature — the single core action the endpoint must support.

**Independent Test**: Can be fully tested by submitting a refund request for a valid, recent, unrefunded order belonging to the authenticated user and verifying the returned refund record contains the order ID, refund timestamp, and refunded amount.

**Acceptance Scenarios**:

1. **Given** an authenticated user has an order created within the last 30 days that has not been refunded, **When** they submit a refund request for that order, **Then** the system marks the order as refunded, records the refund timestamp, and returns the refund record with a success response.

2. **Given** a request with no authentication credentials, **When** a refund request is received, **Then** the system returns a 401 Unauthorized response.

3. **Given** an authenticated user requests a refund for an order ID that does not exist, **When** the request is received, **Then** the system returns a 404 Not Found response.

4. **Given** an authenticated user requests a refund for an order that belongs to a different user, **When** the request is received, **Then** the system returns a 403 Forbidden response.

5. **Given** an authenticated user has an order created more than 30 days ago, **When** they submit a refund request, **Then** the system rejects it with a clear error indicating the refund window has expired.

6. **Given** an authenticated user has an order that has already been refunded, **When** they submit another refund request for the same order, **Then** the system rejects it with a clear error indicating the order was already refunded.

---

### Edge Cases

- What happens when the order's age is exactly 30 days at the moment of the request? — Refund is allowed; the 30-day window is inclusive of day 30.
- What if the order total is zero? — A zero-value refund is still permitted and returns a refund record with a zero amount.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST require the requesting user to be authenticated; reject unauthenticated requests with a 401 error.
- **FR-002**: System MUST verify the requested order exists; return a 404 error if not found.
- **FR-003**: System MUST verify the authenticated user owns the requested order; return a 403 error if they do not.
- **FR-004**: System MUST reject refund requests for orders created more than 30 days before the request, returning a clear error message indicating the window has expired.
- **FR-005**: System MUST reject refund requests for orders that have already been refunded, returning a clear error message.
- **FR-006**: System MUST mark the order as refunded when all validation passes.
- **FR-007**: System MUST record the timestamp at which the refund was processed.
- **FR-008**: System MUST return the refund record — including order ID, refunded amount, and refund timestamp — upon successful processing.
- **FR-009**: The endpoint MUST be covered by automated tests including at least one happy-path test and at least one error-path test, meeting the project's minimum 80% line coverage requirement on changed files.

### Key Entities

- **Order**: A purchase placed by a user. Gains a refunded status and a refund timestamp as part of this feature.
- **Refund Record**: The outcome of a successful refund request. Contains the order identifier, the amount refunded (equal to the original order total), and the timestamp the refund was processed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An authenticated user can successfully request a refund for an eligible order and receive the refund record within a normal API response time.
- **SC-002**: All six acceptance scenarios — one happy path and five error paths — are covered by automated tests that pass consistently.
- **SC-003**: Every ineligible refund attempt (unauthenticated, wrong owner, expired window, already refunded, order not found) always produces a distinct, human-readable error response and never silently succeeds.
- **SC-004**: A refunded order cannot be refunded a second time regardless of request ordering or timing.

## Assumptions

- Authentication uses the existing identity-header mechanism already supported by the service; no new authentication system is introduced.
- The 30-day window is calculated from the order's creation timestamp to the moment the refund request is received (wall-clock time). Day 30 is inclusive.
- The refunded amount is always equal to the original order total; partial refunds are out of scope.
- Refund processing is synchronous and local to this service — no external payment gateway, no asynchronous jobs, no financial settlement.
- Once an order is marked as refunded, the status is permanent. There is no "cancel refund" or "un-refund" capability in scope.
- The existing order data already includes a creation timestamp sufficient to enforce the 30-day rule.
- This feature targets the existing REST API only; no UI, notification, or reporting surface is in scope.
