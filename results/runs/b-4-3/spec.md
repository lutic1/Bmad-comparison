# Feature Specification: Checkout Discount Code

**Feature Branch**: `001-checkout-discount-code`

**Created**: 2026-05-19

**Status**: Draft

**Input**: User description: "Add a feature where users can apply a percentage discount code at checkout. Discounts can be 5%, 10%, or 20%. Include tests."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Apply Valid Discount Code (Priority: P1)

A user enters a discount code during checkout and the system applies the corresponding percentage discount to their order total, showing the reduced price before they confirm the purchase.

**Why this priority**: This is the core value of the feature — without successful discount application, nothing else matters.

**Independent Test**: Can be fully tested by submitting a known valid discount code at checkout and verifying the displayed total reflects the correct percentage reduction.

**Acceptance Scenarios**:

1. **Given** a user has items in their cart and is on the checkout screen, **When** they enter a valid 10% discount code and submit it, **Then** the system displays the original total, the discount amount (10% of original), and the new discounted total.
2. **Given** a user has applied a valid discount code, **When** they confirm the order, **Then** the order is created with the discounted total recorded.
3. **Given** valid discount codes exist for 5%, 10%, and 20%, **When** each is applied to an order with the same total, **Then** the system correctly calculates and displays 5%, 10%, and 20% savings respectively.

---

### User Story 2 - Reject Invalid Discount Code (Priority: P2)

A user enters an unrecognized or invalid discount code and the system informs them clearly, leaving their order total unchanged.

**Why this priority**: Without proper validation and feedback, users cannot distinguish a typo from an expired code, eroding trust.

**Independent Test**: Can be fully tested by submitting an unrecognized discount code string and verifying the order total is unchanged and an error message is displayed.

**Acceptance Scenarios**:

1. **Given** a user is on the checkout screen, **When** they enter a discount code that does not exist, **Then** the system displays an error message and the order total remains unchanged.
2. **Given** a user has entered an invalid discount code, **When** they correct it to a valid code and resubmit, **Then** the discount is applied successfully.

---

### User Story 3 - Remove Applied Discount Code (Priority: P3)

A user who has already applied a discount code can remove it, restoring the original order total.

**Why this priority**: Users may apply a discount by mistake or change their mind; inability to remove it would force order cancellation.

**Independent Test**: Can be fully tested by applying a valid code, then removing it, and verifying the total returns to its original value.

**Acceptance Scenarios**:

1. **Given** a user has applied a valid discount code, **When** they choose to remove the discount, **Then** the order total is restored to the original amount and the discount code field is cleared.

---

### Edge Cases

- What happens when a user tries to apply a second discount code while one is already applied? The second code replaces the first (one code per order at a time).
- What happens when the order total is zero? The discount code can still be applied but the discounted amount is zero.
- What happens if the user modifies their cart (adds/removes items) after applying a discount code? The discount percentage remains applied and recalculates against the new total.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to enter a discount code during checkout before order confirmation.
- **FR-002**: System MUST validate the entered discount code against the set of known valid codes.
- **FR-003**: System MUST support exactly three discount percentages: 5%, 10%, and 20%.
- **FR-004**: System MUST calculate the discounted total by subtracting the code's percentage of the original order total.
- **FR-005**: System MUST display the original total, the discount amount, and the discounted total to the user after a valid code is applied.
- **FR-006**: System MUST reject unrecognized discount codes with a clear, user-facing error message.
- **FR-007**: System MUST allow only one discount code to be active per order at a time; applying a new code replaces the previous one.
- **FR-008**: Users MUST be able to remove an applied discount code, which restores the original order total.
- **FR-009**: System MUST record which discount code and percentage were applied on the completed order.
- **FR-010**: Tests MUST be included covering happy-path application of each discount tier and at least one invalid-code error path.

### Key Entities

- **DiscountCode**: A redeemable code string associated with a fixed percentage (5%, 10%, or 20%). Pre-configured in the system; not user-created in this feature.
- **Order**: A purchase in progress or completed. May have at most one discount code applied. Stores both original total and discounted total when a code is used.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can enter a discount code and see the updated total without leaving the checkout screen.
- **SC-002**: 100% of unrecognized discount codes are rejected with an informative error message before the order is placed.
- **SC-003**: Discount calculations are accurate for all three supported tiers (5%, 10%, 20%) across any order total.
- **SC-004**: Users can remove an applied discount code and the original total is immediately restored without reloading the page or restarting checkout.
- **SC-005**: All new code paths have automated test coverage for at least the happy path and one error path per user story.

## Assumptions

- Discount codes are pre-configured in the system by administrators; creating or managing codes is out of scope for this feature.
- Discount codes do not expire and have no per-user or global usage limits in this version.
- The existing checkout flow is the integration point; this feature adds a discount code input step to it.
- Users must be authenticated to reach checkout (existing auth mechanism applies; no new auth logic required).
- Discounts are applied to the pre-tax order subtotal; tax calculation on the discounted amount is handled by the existing checkout flow.
- Discount code lookup and validation are case-insensitive.
