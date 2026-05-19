# Feature Specification: Order Refund Endpoint

**Feature Branch**: `001-order-refund`

**Created**: 2026-05-19

**Status**: Draft

**Input**: User description: "Add a `POST /orders/{order_id}/refund` endpoint. It should: require authentication, validate the order exists and belongs to the requesting user, only allow refunds within 30 days of order creation, mark the order as refunded (add a field if needed), and return the refund record. Include tests."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Refund an eligible order (Priority: P1)

An authenticated customer who placed an order within the last 30 days wants to
request a refund on that order. They invoke the refund action against the
specific order. The system records the refund, marks the order as refunded, and
returns the refund record to the customer.

**Why this priority**: This is the entire feature. Without it, customers cannot
initiate refunds, and the rest of the rules (ownership, eligibility window) have
nothing to gate.

**Independent Test**: Create an order for a known user, then call the refund
action as that same user within 30 days. Verify a refund record is returned and
the order is marked as refunded.

**Acceptance Scenarios**:

1. **Given** an authenticated user owns an order created 5 days ago and not
   previously refunded, **When** the user requests a refund on that order,
   **Then** the order is marked as refunded and the refund record is returned.
2. **Given** an authenticated user owns an order created 29 days, 23 hours ago,
   **When** the user requests a refund, **Then** the refund succeeds.

---

### User Story 2 - Reject refund for ineligible order (Priority: P2)

An authenticated customer attempts to refund an order that is outside the
30-day window, already refunded, not owned by them, or does not exist. The
system rejects the request with a clear error and does not change order state.

**Why this priority**: These rules protect the business from fraudulent or
invalid refund requests. They are required for the feature to be safe, but the
happy path in P1 demonstrates the core value first.

**Independent Test**: Attempt refund on (a) an order owned by a different user,
(b) an order older than 30 days, (c) an already-refunded order, and (d) a
non-existent order. Each must return an error and leave order state unchanged.

**Acceptance Scenarios**:

1. **Given** an authenticated user, **When** they request a refund on an order
   that belongs to another user, **Then** the request is rejected and the order
   is not modified.
2. **Given** an authenticated user owns an order created 31 days ago, **When**
   they request a refund, **Then** the request is rejected with a reason
   indicating the refund window has passed.
3. **Given** an authenticated user owns an order that has already been
   refunded, **When** they request a refund again, **Then** the request is
   rejected and no new refund record is created.
4. **Given** an authenticated user, **When** they request a refund on an
   `order_id` that does not exist, **Then** the request is rejected as not
   found.

---

### User Story 3 - Reject unauthenticated refund attempt (Priority: P2)

An unauthenticated caller invokes the refund action. The system rejects the
request before any order lookup or state change occurs.

**Why this priority**: Authentication is a precondition for the ownership
check. Without it the ownership rule is meaningless.

**Independent Test**: Call the refund action without authentication credentials
and verify the request is rejected with an authentication error and no order is
modified.

**Acceptance Scenarios**:

1. **Given** no authentication is provided, **When** the refund action is
   invoked, **Then** the request is rejected as unauthenticated and no order
   state changes.

---

### Edge Cases

- Order does not exist for the given `order_id`.
- Order exists but belongs to a different user than the requester.
- Order was created exactly at the 30-day boundary (treated as still eligible;
  see Assumptions).
- Order has already been refunded — second refund attempt must fail.
- Caller is unauthenticated.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST require the caller to be authenticated when
  invoking the refund action. Unauthenticated requests MUST be rejected.
- **FR-002**: The system MUST verify that the order identified by `order_id`
  exists. If it does not, the request MUST be rejected as not found.
- **FR-003**: The system MUST verify that the order belongs to the
  authenticated caller. If it does not, the request MUST be rejected.
- **FR-004**: The system MUST reject refund requests for orders whose creation
  timestamp is more than 30 days before the time of the refund request.
- **FR-005**: The system MUST reject refund requests for orders that are
  already marked as refunded, and MUST NOT create a duplicate refund record.
- **FR-006**: On a successful refund, the system MUST mark the order as
  refunded.
- **FR-007**: On a successful refund, the system MUST create and persist a
  refund record associated with the order.
- **FR-008**: On a successful refund, the system MUST return the refund record
  to the caller.
- **FR-009**: Failed refund attempts MUST NOT modify the order or create a
  refund record.
- **FR-010**: The feature MUST ship with automated tests covering the happy
  path and at least one error path per the project's testing standard.

### Key Entities *(include if feature involves data)*

- **Order**: An existing purchase belonging to a user. Has a creation timestamp
  and an owner. Must gain a way to indicate it has been refunded.
- **Refund**: A record that an order has been refunded. Associated with exactly
  one order. Records when the refund occurred.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An eligible customer can complete a refund request on their own
  order in a single action.
- **SC-002**: 100% of refund attempts on orders not owned by the caller are
  rejected without modifying the order.
- **SC-003**: 100% of refund attempts on orders older than 30 days are
  rejected without modifying the order.
- **SC-004**: 100% of repeat refund attempts on an already-refunded order are
  rejected and result in exactly one refund record for that order.
- **SC-005**: 100% of unauthenticated refund attempts are rejected before any
  order data is read or written.

## Assumptions

- Authentication uses the project's existing mechanism for identifying the
  requesting user; no new auth scheme is introduced by this feature.
- "Within 30 days of order creation" is inclusive of the full 30th day; an
  order created exactly 30 days ago is still eligible. Beyond 30 days is
  ineligible.
- Refunds are all-or-nothing on a single order. Partial refunds are out of
  scope for this feature.
- An order can be refunded at most once.
- The refund record contains, at minimum, an identifier, the associated order,
  and the time the refund was created. No external payment-processor
  integration is in scope; "refund" here means recording the refund in this
  service.
- Currency, amount, and reason fields on the refund record are not required by
  the user request and are out of scope unless added later.
