# Feature Specification: Order Refund

**Feature Branch**: `001-order-refund`

**Created**: 2026-05-19

**Status**: Draft

**Input**: User description: "Add a `POST /orders/{order_id}/refund` endpoint. It should: require authentication, validate the order exists and belongs to the requesting user, only allow refunds within 30 days of order creation, mark the order as refunded (add a field if needed), and return the refund record. Include tests."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Customer refunds a recent order (Priority: P1)

An authenticated customer who placed an order within the last 30 days wants to
get their money back. They submit a refund request against that specific order
and receive confirmation that the refund has been recorded.

**Why this priority**: This is the entire feature. Without this happy path,
nothing else matters — refunds are the value being delivered.

**Independent Test**: Create an order for an authenticated user, request a
refund against it within the 30-day window, and verify the response contains
a refund record and the order is reported as refunded.

**Acceptance Scenarios**:

1. **Given** an authenticated user owns an order created 5 days ago that has
   not been refunded, **When** they submit a refund request for that order,
   **Then** the system records the refund, marks the order as refunded, and
   returns the refund record.
2. **Given** an authenticated user owns an order created 29 days ago that has
   not been refunded, **When** they submit a refund request, **Then** the
   refund is accepted (the 30-day window is still open).

---

### User Story 2 - Refund is rejected when the order is too old (Priority: P2)

A customer attempts to refund an order that was placed more than 30 days ago.
The system declines the request and explains why, so the customer understands
they are outside the refund window.

**Why this priority**: Enforcing the refund window is a business rule that
prevents financial loss; it is essential but secondary to the happy path.

**Independent Test**: Create an order dated 31+ days ago, attempt a refund as
its owner, and verify the request is rejected with a clear reason and the
order remains non-refunded.

**Acceptance Scenarios**:

1. **Given** an authenticated user owns an order created 31 days ago, **When**
   they submit a refund request, **Then** the request is rejected with a
   message indicating the 30-day window has passed and no refund record is
   created.

---

### User Story 3 - Refund is rejected when the caller does not own the order (Priority: P2)

A user attempts to refund an order that belongs to a different user. The
system refuses to act on someone else's order and does not reveal whether the
order exists.

**Why this priority**: Authorization is a security requirement; allowing a
user to refund another user's order would be a serious defect.

**Independent Test**: Create an order owned by user A, attempt a refund as
user B, and verify the request is rejected and no refund record is created.

**Acceptance Scenarios**:

1. **Given** an authenticated user who is not the owner of a given order,
   **When** they submit a refund request for that order, **Then** the request
   is rejected and no refund record is created.
2. **Given** an unauthenticated caller, **When** they submit a refund
   request, **Then** the request is rejected as unauthenticated.

---

### Edge Cases

- A user requests a refund for an `order_id` that does not exist → the
  request is rejected without leaking whether the order ever existed.
- A user requests a refund for an order that has already been refunded → the
  second request is rejected and no duplicate refund record is created.
- A user requests a refund for an order whose creation timestamp is exactly
  30 days old → treated as still inside the window (boundary is inclusive of
  the 30th day).
- The refund request body is empty or malformed → the request is rejected
  with a clear validation error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose a way to request a refund against a
  specific existing order, identified by its order ID.
- **FR-002**: The system MUST require the caller to be authenticated before
  processing any refund request.
- **FR-003**: The system MUST verify that the order identified in the request
  exists and is owned by the authenticated caller; if either check fails, the
  refund MUST be rejected and no refund record created.
- **FR-004**: The system MUST reject any refund request submitted more than
  30 days after the order's creation timestamp.
- **FR-005**: The system MUST mark a successfully refunded order as refunded
  so that its refunded state is visible on future reads of the order.
- **FR-006**: The system MUST prevent the same order from being refunded more
  than once.
- **FR-007**: On a successful refund, the system MUST return a refund record
  that identifies the refund, the order it applies to, and when the refund
  occurred.
- **FR-008**: The system MUST distinguish, in its responses, between the
  following failure modes so the caller can react appropriately: not
  authenticated, not authorized / order not found, refund window expired,
  order already refunded.
- **FR-009**: The behaviour above MUST be covered by automated tests,
  including at minimum the happy path and one test per error path called
  out in FR-008.

### Key Entities *(include if feature involves data)*

- **Order**: An existing purchase belonging to a user. Relevant attributes
  for this feature: identity, owning user, creation timestamp, and a
  refunded state.
- **Refund**: A record produced when an order is successfully refunded.
  Relevant attributes: identity, the order it refers to, and the time the
  refund was recorded.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An eligible owner can request and receive confirmation of a
  refund on one of their orders in a single request.
- **SC-002**: 100% of refund attempts on orders older than 30 days are
  rejected.
- **SC-003**: 100% of refund attempts by a user who is not the owner of the
  target order are rejected, and no information distinguishing "not yours"
  from "does not exist" is leaked to the caller.
- **SC-004**: No order can end up with more than one refund record under any
  sequence of refund requests.
- **SC-005**: Automated tests cover the happy path and each of the four
  failure modes listed in FR-008, and all pass.

## Assumptions

- Authentication uses the project's existing mechanism for identifying the
  calling user; no new auth scheme is introduced by this feature.
- "Within 30 days of order creation" is measured from the order's recorded
  creation timestamp to the time the refund request is received, inclusive
  of the 30th day.
- Refunds in this feature are recorded only — actual money movement with a
  payment processor is out of scope.
- Partial refunds are out of scope; a refund applies to the whole order.
- The response indicating "not authorized" and "order not found" is the same
  to avoid leaking the existence of other users' orders.
