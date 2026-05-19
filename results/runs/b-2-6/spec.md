# Feature Specification: Order Refund

**Feature Branch**: `001-order-refund`

**Created**: 2026-05-19

**Status**: Draft

**Input**: User description: "Add a `POST /orders/{order_id}/refund` endpoint. It should: require authentication, validate the order exists and belongs to the requesting user, only allow refunds within 30 days of order creation, mark the order as refunded (add a field if needed), and return the refund record. Include tests."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Refund a recent own order (Priority: P1)

A signed-in customer who placed an order within the last 30 days can request a
refund for that order and receive confirmation of the refund.

**Why this priority**: This is the entire feature — without the happy path the
endpoint has no value.

**Independent Test**: Authenticate as the order's owner, submit a refund
request against an order created within the past 30 days, and confirm that a
refund record is returned and that the order is reflected as refunded on
subsequent reads.

**Acceptance Scenarios**:

1. **Given** an authenticated customer who owns order `O` created 5 days ago and
   not yet refunded, **When** they request a refund for `O`, **Then** the system
   records the refund, marks the order as refunded, and returns the refund
   record.
2. **Given** an order has just been refunded, **When** the customer fetches the
   order, **Then** its refunded status is visible.

---

### User Story 2 - Refund is rejected for ineligible orders (Priority: P1)

A signed-in customer attempts to refund an order that is not eligible (does not
exist, is owned by someone else, is older than 30 days, or has already been
refunded) and receives a clear rejection without any state change.

**Why this priority**: Without these guards the endpoint would allow theft,
information leakage about other users' orders, and double refunds. Equal
priority to the happy path.

**Independent Test**: As an authenticated customer, attempt each of the
ineligible scenarios in turn and verify that the request is rejected and the
order's refund state is unchanged.

**Acceptance Scenarios**:

1. **Given** the requested order does not exist, **When** the customer requests
   a refund, **Then** the request is rejected as not found.
2. **Given** the requested order belongs to a different user, **When** the
   customer requests a refund, **Then** the request is rejected and no
   information about the order is disclosed.
3. **Given** the requested order was created more than 30 days ago, **When** the
   customer requests a refund, **Then** the request is rejected as outside the
   refund window.
4. **Given** the requested order has already been refunded, **When** the
   customer requests a refund again, **Then** the request is rejected and no
   second refund record is created.

---

### User Story 3 - Unauthenticated requests are refused (Priority: P1)

An unauthenticated caller attempts to refund an order and is refused before any
order lookup occurs.

**Why this priority**: Authentication is a baseline requirement called out
explicitly in the feature request.

**Independent Test**: Send a refund request without authentication credentials
and verify that the request is refused.

**Acceptance Scenarios**:

1. **Given** no authentication is provided, **When** the caller requests a
   refund for any order id, **Then** the request is refused as unauthenticated.

---

### Edge Cases

- A refund request arrives exactly at the 30-day boundary — the cutoff is
  inclusive of the 30th day and exclusive thereafter.
- A refund request targets a malformed or non-numeric order id — handled as a
  not-found / invalid input rather than a server error.
- Two refund requests for the same order arrive in close succession — only one
  refund record is created; the second is rejected as already refunded.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose a way to request a refund for a specific
  order, identified by its order id.
- **FR-002**: The system MUST require the caller to be authenticated; an
  unauthenticated refund request MUST be refused without state change.
- **FR-003**: The system MUST reject a refund request when the target order
  does not exist.
- **FR-004**: The system MUST reject a refund request when the target order is
  not owned by the requesting user, and MUST NOT reveal whether such an order
  exists.
- **FR-005**: The system MUST only permit refunds for orders whose creation
  time is within the last 30 days (inclusive of day 30).
- **FR-006**: The system MUST reject a refund request for an order that has
  already been refunded, and MUST NOT create a duplicate refund record.
- **FR-007**: On a successful refund, the system MUST mark the order as
  refunded so that the refunded state is observable on subsequent reads of the
  order.
- **FR-008**: On a successful refund, the system MUST return a refund record
  that identifies the refund, the order it applies to, and the time it was
  issued.
- **FR-009**: The feature MUST ship with automated tests covering the happy
  path and at least one rejection path per the project's testing standard.

### Key Entities *(include if feature involves data)*

- **Order**: An existing customer order. Gains an observable refunded state
  (and the time at which it was refunded) as a result of this feature.
- **Refund**: A record that an order was refunded. Identifies the refund, the
  order it belongs to, and when it was issued. One order has at most one
  refund.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of refund requests by an authenticated owner for an
  un-refunded order created within the last 30 days succeed and produce a
  refund record.
- **SC-002**: 100% of refund requests that violate authentication, ownership,
  the 30-day window, or the no-double-refund rule are rejected without
  modifying the order's refunded state and without creating a refund record.
- **SC-003**: After a successful refund, the order's refunded state is
  observable on the very next read of that order.
- **SC-004**: The feature ships with automated tests that cover the happy path
  and each rejection path described above, and the test suite passes.

## Assumptions

- "Belongs to the requesting user" means the order's owner id equals the
  authenticated caller's user id; this matches how the existing service already
  identifies the current user.
- The 30-day refund window is measured from the order's recorded creation time
  to the time the refund request is processed, in the same time reference the
  service already uses for order timestamps.
- An order may be refunded at most once. Partial refunds are out of scope.
- No external payment processor integration is in scope; "refund" here is the
  service's own bookkeeping action.
- No notification, email, or audit-log side effects are in scope beyond
  recording the refund and marking the order.
- The refund record's identifier scheme follows whatever convention the
  service already uses for primary identifiers on its records.
