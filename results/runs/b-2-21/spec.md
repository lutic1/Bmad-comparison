# Feature Specification: Order Refund

**Feature Branch**: `001-order-refund`

**Created**: 2026-05-19

**Status**: Draft

**Input**: User description: "Add a `POST /orders/{order_id}/refund` endpoint. It should: require authentication, validate the order exists and belongs to the requesting user, only allow refunds within 30 days of order creation, mark the order as refunded (add a field if needed), and return the refund record. Include tests."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Customer refunds a recent order (Priority: P1)

An authenticated customer requests a refund on an order they own that was
placed within the last 30 days. The system records the refund, marks the
order as refunded, and returns the refund record so the customer (or the
client app on their behalf) has confirmation.

**Why this priority**: This is the entire feature. Without it, customers
cannot self-serve refunds for recent purchases — which is the value the
endpoint exists to deliver.

**Independent Test**: As an authenticated user, submit a refund request
for an order you own that was created less than 30 days ago, and confirm
the response contains a refund record and that subsequent reads of the
order show it as refunded.

**Acceptance Scenarios**:

1. **Given** an authenticated user owns order O created 5 days ago and O
   is not yet refunded, **When** the user submits a refund request for O,
   **Then** the system records a refund, marks O as refunded, and
   returns the refund record.
2. **Given** order O has already been refunded, **When** the same user
   submits another refund request for O, **Then** the system rejects the
   request and does not create a duplicate refund.

---

### User Story 2 - Refund attempt is rejected when ineligible (Priority: P1)

A requester attempts to refund an order that they don't own, that
doesn't exist, or that is older than 30 days. The system rejects the
request with a clear error and does not modify any order.

**Why this priority**: Without rejection paths, the feature would expose
customer data across accounts and allow refunds outside the policy
window — both of which violate the requested constraints.

**Independent Test**: Make refund requests against (a) a non-existent
order id, (b) an order owned by a different user, and (c) an order
created more than 30 days ago, and confirm each is rejected and no order
state changes.

**Acceptance Scenarios**:

1. **Given** no order exists with id X, **When** an authenticated user
   submits a refund request for X, **Then** the system rejects the
   request as not found.
2. **Given** order O exists but belongs to a different user, **When** an
   authenticated user submits a refund request for O, **Then** the
   system rejects the request and O is unchanged.
3. **Given** order O is owned by the requester but was created 31 days
   ago, **When** the user submits a refund request for O, **Then** the
   system rejects the request as outside the refund window and O is
   unchanged.

---

### User Story 3 - Unauthenticated refund attempt is rejected (Priority: P1)

A request to the refund endpoint without authentication credentials is
rejected before any order lookup or state change occurs.

**Why this priority**: Authentication is an explicit requirement;
without it, anyone could refund any order.

**Independent Test**: Submit a refund request with no authentication
header and confirm the request is rejected and no order state changes.

**Acceptance Scenarios**:

1. **Given** no authentication is provided, **When** a refund request is
   submitted for any order, **Then** the system rejects the request as
   unauthenticated and performs no order lookup or modification.

---

### Edge Cases

- A second refund request for an order already marked refunded MUST be
  rejected (no duplicate refund records, no double processing).
- A refund request submitted exactly 30 days after order creation is
  considered within the window; one submitted at 30 days + any amount of
  time after is outside the window.
- A refund request for an order id that is malformed or non-numeric MUST
  be rejected as a bad request.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST require authentication on the refund endpoint
  and reject unauthenticated requests before performing any order
  lookup or state change.
- **FR-002**: System MUST verify the targeted order exists and reject
  the request when it does not.
- **FR-003**: System MUST verify the targeted order belongs to the
  authenticated requester and reject the request when it does not.
- **FR-004**: System MUST reject refund requests for orders created more
  than 30 days before the request time.
- **FR-005**: System MUST mark the order as refunded upon a successful
  refund, persisting this state on the order record.
- **FR-006**: System MUST create and persist a refund record for each
  successful refund.
- **FR-007**: System MUST reject a refund request for an order that is
  already marked refunded, and MUST NOT create a duplicate refund
  record.
- **FR-008**: System MUST return the refund record in the response of a
  successful refund request.
- **FR-009**: Feature MUST ship with automated tests covering the
  happy path and the rejection paths (unauthenticated, not found,
  not owned, outside 30-day window, already refunded).

### Key Entities *(include if feature involves data)*

- **Order**: The existing order being refunded. Must carry a refunded
  state (added if not already present) and retain its creation
  timestamp so the 30-day window can be evaluated.
- **Refund**: A record produced when a refund succeeds. Associates with
  the order it refunds and captures when the refund was issued.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of refund requests that meet all eligibility
  conditions (authenticated, order exists, order belongs to requester,
  within 30 days, not already refunded) result in the order being
  marked refunded and a refund record returned to the requester.
- **SC-002**: 100% of refund requests that fail any one of those
  conditions are rejected and leave the order unchanged.
- **SC-003**: No refund request results in more than one refund record
  for the same order.
- **SC-004**: Automated tests cover the happy path and every documented
  rejection path, and all pass.

## Assumptions

- Authentication uses the project's existing user-identification
  mechanism for protected endpoints; no new auth scheme is being
  introduced as part of this feature.
- "Within 30 days" is measured as the elapsed time between the order's
  creation timestamp and the time the refund request is received,
  with 30 days treated as inclusive.
- Refunds in this feature are an internal state change and recording
  step; no integration with an external payment processor is in scope.
- The refund amount equals the order's full amount; partial refunds are
  out of scope for this feature.
- Only the order's owner can initiate a refund through this endpoint;
  administrative or support-initiated refunds are out of scope.
