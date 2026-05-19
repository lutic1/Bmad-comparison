# Feature Specification: Order Refund

**Feature Branch**: `001-order-refund`

**Created**: 2026-05-19

**Status**: Draft

**Input**: User description: "Add a `POST /orders/{order_id}/refund` endpoint. It should require authentication, validate the order exists and belongs to the requesting user, only allow refunds within 30 days of order creation, mark the order as refunded (add a field if needed), and return the refund record. Include tests."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Successful Order Refund (Priority: P1)

An authenticated user submits a refund request for one of their own orders that was created within the last 30 days. The system validates eligibility, marks the order as refunded, and returns a refund confirmation record.

**Why this priority**: This is the core happy path of the feature — delivering value by allowing users to process refunds. All other stories are guard rails around this flow.

**Independent Test**: Can be fully tested by creating an order, immediately requesting a refund, and verifying the returned refund record matches the order data and the order is now marked refunded.

**Acceptance Scenarios**:

1. **Given** an authenticated user with a valid order they own that was created within 30 days, **When** they submit a refund request for that order, **Then** the system returns a refund record containing the order ID, user ID, and refund timestamp, and the order is permanently marked as refunded.
2. **Given** an authenticated user with a valid order created at exactly the 30-day boundary, **When** they submit a refund request, **Then** the request is accepted and a refund record is returned.

---

### User Story 2 - Refund Rejection (Priority: P2)

An authenticated user attempts to request a refund that the system must not process: the order is too old, belongs to another user, does not exist, or has already been refunded. The system rejects each case with a clear, specific error.

**Why this priority**: Without rejection handling the system would allow fraudulent and duplicate refunds. This is critical for correctness but secondary to establishing the happy path.

**Independent Test**: Can be tested independently by attempting a refund under each invalid condition and verifying the appropriate error response is returned.

**Acceptance Scenarios**:

1. **Given** an authenticated user, **When** they request a refund for an order created more than 30 days ago, **Then** the system returns an error indicating the refund window has expired.
2. **Given** an authenticated user, **When** they request a refund for an order that belongs to a different user, **Then** the system returns a not-found error (to avoid disclosing order existence to unauthorized users).
3. **Given** an authenticated user, **When** they request a refund for an order that does not exist, **Then** the system returns a not-found error.
4. **Given** an authenticated user, **When** they request a refund for an order that has already been refunded, **Then** the system returns an error indicating a duplicate refund attempt.
5. **Given** an unauthenticated request, **When** a refund is attempted, **Then** the system returns an authentication error.

---

### Edge Cases

- What happens when a refund is requested at exactly the 30-day mark (boundary condition)?
- What happens when the same order receives concurrent refund requests?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST require user authentication to access the refund endpoint; unauthenticated requests MUST be rejected.
- **FR-002**: System MUST reject refund requests for orders that do not exist, returning a not-found error.
- **FR-003**: System MUST reject refund requests for orders that do not belong to the requesting user, returning a not-found error (ownership must not be disclosed to unauthorized requestors).
- **FR-004**: System MUST reject refund requests for orders created more than 30 days prior to the request, returning an error that indicates the refund window has expired.
- **FR-005**: System MUST reject duplicate refund requests for an order that has already been refunded.
- **FR-006**: System MUST mark an eligible order as refunded and record the refund timestamp when a valid refund request is processed.
- **FR-007**: System MUST return a refund record containing the order ID, user ID, and refund timestamp upon successful processing.

### Key Entities

- **Order**: Represents a user's purchase. Has an owner (user), a creation timestamp, a refunded status flag, and (when refunded) a refund timestamp.
- **Refund Record**: A confirmation object returned after a successful refund, containing the order identifier, the requesting user's identifier, and the timestamp when the refund was processed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete a refund request for an eligible order in a single interaction with no ambiguity about the outcome.
- **SC-002**: Every ineligible refund attempt (expired window, wrong owner, non-existent order, duplicate) is rejected with a distinct, informative error — zero cases are silently ignored or incorrectly accepted.
- **SC-003**: Once an order is marked as refunded, all subsequent refund attempts on the same order are always rejected — the refunded state is permanent.
- **SC-004**: The 30-day eligibility boundary is enforced exactly; an order created 30 days and 1 second ago is rejected, an order created at exactly 30 days is accepted.

## Assumptions

- Authentication uses the existing authentication mechanism already present in the service; no new auth scheme is introduced.
- "30 days" is calculated as exactly 30 × 24 × 60 × 60 seconds from the order's creation timestamp (not calendar days or business days).
- A refund record is a response-only structure; the order entity itself is the persistent source of truth for refund state.
- No external payment gateway or financial system integration is in scope — this feature marks orders as refunded at the data level only.
- Tests cover the happy path and each rejection scenario individually, following the project's existing test conventions.
