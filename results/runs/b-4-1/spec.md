# Feature Specification: Discount Code at Checkout

**Feature Branch**: `001-discount-codes`

**Created**: 2026-05-18

**Status**: Draft

**Input**: User description: "Add a feature where users can apply a percentage discount code at checkout. Discounts can be 5%, 10%, or 20%. Include tests."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Apply Valid Discount Code (Priority: P1)

A user at checkout enters a discount code. The system validates the code,
applies the corresponding percentage discount (5%, 10%, or 20%) to the
order total, and shows the updated price breakdown before the user confirms
the order.

**Why this priority**: Core feature value — without this, the discount
feature does not exist.

**Independent Test**: Can be fully tested by submitting a known valid
discount code during checkout and verifying the discounted total is
correctly calculated and displayed.

**Acceptance Scenarios**:

1. **Given** a user has items in their order and a valid 10% discount code,
   **When** they submit the code at checkout,
   **Then** the system displays the original total, a 10% discount amount,
   and the reduced final total.

2. **Given** a user has items in their order and a valid 5% discount code,
   **When** they submit the code,
   **Then** the discounted total reflects exactly a 5% reduction on the
   order subtotal.

3. **Given** a user has items in their order and a valid 20% discount code,
   **When** they submit the code,
   **Then** the discounted total reflects exactly a 20% reduction on the
   order subtotal.

---

### User Story 2 - Reject Invalid Discount Code (Priority: P2)

A user at checkout enters a code that does not exist or is not active.
The system rejects it with a clear error message and leaves the order
total unchanged.

**Why this priority**: Prevents confusion and ensures discounts are only
granted for legitimate codes.

**Independent Test**: Can be fully tested by submitting an unrecognised or
inactive code and confirming the error message appears and the total is
unchanged.

**Acceptance Scenarios**:

1. **Given** a user enters a code that does not exist,
   **When** they submit it,
   **Then** the system displays an error ("Invalid discount code") and the
   order total remains unchanged.

2. **Given** a user enters a code that exists but is marked inactive,
   **When** they submit it,
   **Then** the system displays an error ("Discount code is no longer
   active") and the order total remains unchanged.

---

### User Story 3 - One Discount Code Per Order (Priority: P3)

A user who has already applied a discount code cannot stack a second code
on the same order. The system rejects the second code with an informative
message.

**Why this priority**: Prevents discount abuse; a single code per order is
the standard commerce expectation.

**Independent Test**: Can be fully tested by applying a valid code, then
attempting to apply a second valid code on the same order and verifying
the second attempt is rejected.

**Acceptance Scenarios**:

1. **Given** a user has already applied a valid discount code to their order,
   **When** they try to apply another code,
   **Then** the system rejects it with a message indicating a discount has
   already been applied.

---

### Edge Cases

- What happens when the order total is zero?
- How does the system handle a discount code submitted with leading/trailing
  whitespace?
- What happens when a code is submitted with mixed case (e.g., "SAVE10" vs
  "save10")?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow a user to submit a discount code during
  checkout.
- **FR-002**: System MUST validate the submitted code against the set of
  active discount codes.
- **FR-003**: System MUST support exactly three discount tiers: 5%, 10%,
  and 20%.
- **FR-004**: System MUST calculate the discounted order total by applying
  the code's percentage to the order subtotal.
- **FR-005**: System MUST display the original subtotal, the discount
  percentage, the discount amount, and the final total after a valid code
  is applied.
- **FR-006**: System MUST reject invalid or inactive codes with a
  descriptive error message without modifying the order total.
- **FR-007**: System MUST enforce a limit of one discount code per order.
- **FR-008**: System MUST trim whitespace from submitted codes before
  validation and treat codes as case-insensitive.

### Key Entities

- **DiscountCode**: Represents a redeemable code with an associated discount
  percentage (5, 10, or 20) and an active/inactive status.
- **Order**: Represents a user's checkout session, including the subtotal,
  any applied discount code, and the resulting final total.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can apply a discount code and see the updated price
  breakdown in under 2 seconds.
- **SC-002**: Discount calculations are accurate (correct percentage
  applied, rounded to two decimal places).
- **SC-003**: 100% of invalid or inactive codes are rejected without
  modifying the order total.
- **SC-004**: Users receive a clear, actionable error message for every
  rejection scenario (invalid code, inactive code, duplicate code).
- **SC-005**: Test suite covers the happy path for each discount tier
  (5%, 10%, 20%) and every defined error path.

## Assumptions

- Discount codes are created and managed by administrators via a separate
  mechanism (not in scope for this feature).
- The discount applies to the order subtotal before any taxes or shipping
  fees.
- Code validation is performed server-side; client-side behaviour is out of
  scope.
- A discount code remains valid indefinitely unless explicitly deactivated.
- The existing order/checkout flow is already in place; this feature adds
  discount code support to it.
