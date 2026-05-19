# Feature Specification: Discount Codes at Checkout

**Feature Branch**: `001-discount-codes`

**Created**: 2026-05-19

**Status**: Draft

**Input**: User description: "Add a feature where users can apply a percentage discount code at checkout. Discounts can be 5%, 10%, or 20%. Include tests."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Apply Valid Discount Code (Priority: P1)

A user entering a valid discount code at checkout receives an updated order
total reflecting the applicable percentage reduction (5%, 10%, or 20%).

**Why this priority**: Core feature value — without successful code application
the entire feature delivers no user benefit.

**Independent Test**: Can be fully tested by submitting a checkout request
with a known valid discount code and verifying the returned total matches the
expected discounted amount.

**Acceptance Scenarios**:

1. **Given** a user has items in their cart with a known total, **When** they
   apply a valid 10% discount code at checkout, **Then** the order total is
   reduced by exactly 10% and the applied code is recorded on the order.
2. **Given** a valid 5% discount code, **When** applied at checkout, **Then**
   the final total reflects a 5% reduction.
3. **Given** a valid 20% discount code, **When** applied at checkout, **Then**
   the final total reflects a 20% reduction.

---

### User Story 2 - Reject Invalid Discount Code (Priority: P2)

A user who enters an unrecognised or invalid discount code at checkout receives
a clear error message and the order is not placed with an incorrect total.

**Why this priority**: Prevents revenue loss and user confusion from incorrect
discounts being applied silently.

**Independent Test**: Can be fully tested by submitting a checkout request with
a non-existent code and verifying that an error response is returned with no
order created.

**Acceptance Scenarios**:

1. **Given** a user submits an unrecognised discount code, **When** they
   attempt to check out, **Then** the system rejects the request with a clear
   error identifying the code as invalid.
2. **Given** a user submits an empty discount code field, **When** they attempt
   to check out with a discount, **Then** the system returns a validation error.

---

### User Story 3 - Checkout Without Discount Code (Priority: P3)

A user who does not provide a discount code can still complete checkout
normally, with no discount applied.

**Why this priority**: Ensures backward compatibility — existing checkout flow
must not be broken by the addition of the discount feature.

**Independent Test**: Can be fully tested by submitting a checkout request
without a discount code and verifying the order total is unchanged.

**Acceptance Scenarios**:

1. **Given** a user provides no discount code, **When** they check out, **Then**
   the order is placed at the full original total with no discount recorded.

---

### Edge Cases

- What happens when the discount code field is present but blank or whitespace-only?
- What happens when the same valid code is submitted twice in rapid succession
  (duplicate submission guard)?
- What happens when the order total is zero before the discount is applied?
- What happens when the code string contains unexpected characters or unusual casing?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to submit an optional discount code as
  part of the checkout request.
- **FR-002**: System MUST validate that a submitted discount code exists and is
  one of the recognised codes tied to 5%, 10%, or 20% discount rates.
- **FR-003**: System MUST reject unrecognised discount codes with a descriptive
  error message before placing the order.
- **FR-004**: System MUST calculate the discounted order total by applying the
  code's associated percentage to the pre-discount total.
- **FR-005**: System MUST record the applied discount code and the resulting
  discounted total on the completed order.
- **FR-006**: System MUST allow checkout to proceed without a discount code,
  leaving the order total unchanged.
- **FR-007**: System MUST treat discount code lookup as case-insensitive to
  prevent user frustration from capitalisation mismatches.

### Key Entities

- **Discount Code**: A recognisable string that maps to a fixed discount
  percentage (5%, 10%, or 20%). Multiple codes may share the same percentage.
- **Order**: Existing entity extended to carry an optional applied discount code
  reference and the final discounted total.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can apply a discount code and receive a corrected order
  total within the same checkout interaction, with no additional steps required.
- **SC-002**: 100% of orders placed with a valid discount code reflect the
  mathematically correct discounted total (no rounding errors beyond standard
  currency precision).
- **SC-003**: 100% of invalid or unrecognised discount codes are rejected before
  an order is created, with an error message that identifies the problem.
- **SC-004**: Checkout without a discount code continues to succeed at the same
  rate as before the feature was introduced (no regression).
- **SC-005**: All new behaviour is covered by automated tests, with at least
  one happy-path and one error-path test per user story.

## Assumptions

- Discount codes are pre-loaded into the system by operators; there is no
  self-service code creation in this feature.
- Each discount code maps to exactly one percentage value (5%, 10%, or 20%);
  multiple codes may share a percentage.
- Discount codes are reusable across different users and orders (not
  single-use) unless a future requirement specifies otherwise.
- Only one discount code may be applied per order.
- The discount is applied to the gross order total before any other
  adjustments (taxes, shipping, etc. are out of scope for this service).
- Automated tests covering happy-path and error-path scenarios are explicitly
  in scope as stated in the feature description.
