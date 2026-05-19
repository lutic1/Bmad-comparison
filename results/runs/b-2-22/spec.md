# Feature Specification: Order Refund

**Feature Branch**: `001-order-refund`

**Created**: 2026-05-19

**Status**: Draft

**Input**: User description: "Add a `POST /orders/{order_id}/refund` endpoint. It should: require authentication, validate the order exists and belongs to the requesting user, only allow refunds within 30 days of order creation, mark the order as refunded (add a field if needed), and return the refund record. Include tests."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Refund a recent order (Priority: P1)

A signed-in customer who placed an order within the past 30 days wants to
get their money back on that order. They submit a refund request against
the specific order they own, and the system confirms the refund by
returning a refund record and marking the order as refunded.

**Why this priority**: This is the entire feature. Without it the
customer has no path to a refund through the service.

**Independent Test**: Sign in as a customer with one order created less
than 30 days ago, submit a refund request for that order, and confirm
that the response contains a refund record and that the order is
subsequently shown as refunded.

**Acceptance Scenarios**:

1. **Given** an authenticated customer with an order they own that was
   created within the last 30 days, **When** they request a refund on
   that order, **Then** the system records the refund, marks the order
   as refunded, and returns the refund record.
2. **Given** an authenticated customer who has already successfully
   refunded one of their orders, **When** they later view that order,
   **Then** the order is shown as refunded.

---

### Edge Cases

- **Unauthenticated request**: A refund request that does not identify a
  user is rejected as unauthorized.
- **Order does not exist**: A refund request that references an unknown
  order id is rejected as not found.
- **Order belongs to a different user**: A refund request from a user
  who is not the owner of the order is rejected — the response must not
  reveal whether the order exists.
- **Order is older than 30 days**: A refund request against an order
  whose creation timestamp is more than 30 days in the past is
  rejected with a clear reason (refund window expired).
- **Order already refunded**: A second refund request against an order
  that has already been refunded is rejected.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST require an authenticated requester for
  every refund request. Unauthenticated requests MUST be rejected.
- **FR-002**: The system MUST verify that the referenced order exists.
  Requests for unknown orders MUST be rejected as not found.
- **FR-003**: The system MUST verify that the referenced order belongs
  to the requesting user. Requests against orders owned by another
  user MUST be rejected and MUST NOT disclose whether the order
  exists.
- **FR-004**: The system MUST reject refund requests for orders whose
  creation timestamp is more than 30 days before the time the request
  is received, with an error explaining that the refund window has
  expired.
- **FR-005**: When a refund is accepted, the system MUST mark the order
  as refunded in persistent storage so that the refunded state is
  visible to subsequent reads of the order.
- **FR-006**: When a refund is accepted, the system MUST create and
  persist a refund record associated with the order, and MUST return
  that refund record in the response.
- **FR-007**: The system MUST reject refund requests against orders
  that have already been refunded.

### Key Entities *(include if feature involves data)*

- **Order**: An existing concept in the system. For this feature, the
  order must expose its creation timestamp, its owning user, and a
  refunded state. A "refunded" attribute is added if one does not
  already exist.
- **Refund record**: A new persistent record produced when an order is
  refunded. It identifies the refunded order, the user who initiated
  the refund, and the time the refund was issued.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An eligible owner (authenticated, owns the order, order
  created within 30 days, not previously refunded) can successfully
  obtain a refund 100% of the time.
- **SC-002**: 100% of refund attempts that violate any eligibility rule
  (unauthenticated, non-owner, expired window, already refunded,
  unknown order) are rejected with a clear, distinguishable error
  outcome.
- **SC-003**: After a successful refund, the order is observably
  refunded on every subsequent read of that order.
- **SC-004**: The feature ships with automated tests covering the
  happy path and each rejection case enumerated in Edge Cases, and
  those tests pass on every commit.

## Assumptions

- The feature reuses the service's existing authentication mechanism
  for identifying the requesting user; no new authentication scheme
  is introduced.
- Refunds are full refunds of the order. Partial refunds are out of
  scope for this feature.
- At most one refund per order. Once an order is refunded it cannot be
  refunded again.
- The refund operation is a system-of-record action: the service
  records that a refund was issued. Integration with an external
  payment processor to actually move money is out of scope for this
  feature.
- The 30-day window is measured from the order's creation timestamp
  to the time the refund request is received by the service, using
  the service's clock.
- The shape of the refund record returned to the client is minimal
  but sufficient to identify the refund and the order it refunded
  (e.g., refund id, order id, refund timestamp).
