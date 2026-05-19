# Feature Specification: Percentage Discount Codes at Checkout

**Feature Branch**: `001-discount-codes`

**Created**: 2026-05-19

**Status**: Draft

**Input**: User description: "Add a feature where users can apply a percentage discount code at checkout. Discounts can be 5%, 10%, or 20%. Include tests."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Apply a valid discount code at checkout (Priority: P1)

A shopper has goods in their order and a promotional code shared via email
or marketing. At checkout they enter the code, and the order total is
reduced by the corresponding percentage (5%, 10%, or 20%) before they
confirm the order.

**Why this priority**: This is the core capability the feature exists to
deliver. Without it, none of the other scenarios are reachable.

**Independent Test**: With an order containing at least one item and a
known valid code, submitting the code at checkout reduces the displayed
order total by the correct percentage and the confirmed order reflects
that discounted total.

**Acceptance Scenarios**:

1. **Given** a checkout with a subtotal of 100.00 and a valid 10% code,
   **When** the shopper applies the code, **Then** the order total
   becomes 90.00 and the discount amount (10.00) is shown alongside the
   subtotal.
2. **Given** a checkout with a subtotal of 50.00 and a valid 20% code,
   **When** the shopper applies the code, **Then** the order total
   becomes 40.00.
3. **Given** a checkout with a valid 5% code applied, **When** the
   shopper confirms the order, **Then** the confirmed order persists the
   discounted total and records which code was used.

---

### User Story 2 - Reject an invalid or unknown discount code (Priority: P2)

A shopper enters a code that does not exist, is misspelled, or is not one
of the recognized promotional codes. The system must refuse to apply it
and tell the shopper why, without changing the order total.

**Why this priority**: Without graceful rejection, shoppers either get
silent failures or unintended discounts. This protects revenue and the
checkout UX.

**Independent Test**: Entering a code that is not on the recognized list
returns a clear "invalid code" response and leaves the order total
unchanged.

**Acceptance Scenarios**:

1. **Given** a checkout with subtotal 100.00, **When** the shopper
   applies the code `NOPE123`, **Then** the request is rejected with a
   message indicating the code is invalid and the total remains 100.00.
2. **Given** a checkout with subtotal 100.00, **When** the shopper
   applies an empty code, **Then** the request is rejected and the total
   remains 100.00.

---

### User Story 3 - Replace a previously applied code (Priority: P3)

A shopper applies one valid code, then decides to try a different one
(e.g., they received a better promo). Applying the second valid code
replaces the first; only one discount is in effect at a time.

**Why this priority**: Avoids stacking discounts beyond what the
business has authorized, while still giving shoppers a way to change
their mind.

**Independent Test**: After applying a 5% code and then a 20% code on
the same checkout, the order total reflects 20% off the original
subtotal — not 5% + 20% combined, and not 20% off the already-discounted
total.

**Acceptance Scenarios**:

1. **Given** a checkout with subtotal 100.00 and a 5% code already
   applied (total 95.00), **When** the shopper applies a valid 20% code,
   **Then** the new order total is 80.00 (20% off the original subtotal).

---

### Edge Cases

- Empty order (no items / subtotal of 0): applying any valid code yields
  a total of 0.00 and is accepted (the discount has no effect but is not
  an error).
- Codes are case-insensitive: `save10` and `SAVE10` resolve to the same
  code.
- Rounding: the discount is computed on the subtotal in the order's
  currency unit; the resulting total is rounded to two decimal places
  using standard half-up rounding.
- A discount code only affects the order it is applied to; it does not
  retroactively change previously confirmed orders.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The checkout flow MUST accept a discount code submitted by
  the shopper as part of applying it to a pending order.
- **FR-002**: The system MUST recognize exactly three valid discount
  percentages: 5%, 10%, and 20%. Codes mapping to any other percentage
  MUST be rejected as invalid.
- **FR-003**: When a valid code is applied, the system MUST compute the
  discounted total as `subtotal - (subtotal * percentage / 100)`,
  rounded to two decimal places.
- **FR-004**: The system MUST return, for any discount application
  attempt, both the original subtotal and the resulting total (or an
  explicit error if rejected).
- **FR-005**: The system MUST reject unknown, empty, or malformed codes
  with a clear error indicating the code is not valid, and MUST NOT
  change the order total in those cases.
- **FR-006**: Discount code lookup MUST be case-insensitive.
- **FR-007**: At most one discount code MAY be in effect on an order at
  a time. Applying a new valid code replaces any previously applied code.
- **FR-008**: When a shopper confirms an order with a discount applied,
  the confirmed order MUST persist the discounted total and a reference
  to the code that was used.
- **FR-009**: The feature MUST ship with automated tests covering at
  least: each of the three valid percentages, an invalid-code rejection,
  and the replace-existing-code behavior.

### Key Entities *(include if feature involves data)*

- **Discount Code**: A short, case-insensitive string a shopper enters
  at checkout. Maps to exactly one of the supported percentages (5%,
  10%, 20%).
- **Order (at checkout)**: Has a subtotal derived from its items, an
  optional applied discount code, and a resulting total. Once confirmed,
  the discount code and discounted total are recorded on the order.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of checkouts that apply one of the three supported
  codes against a non-empty order see the correct percentage reduction
  reflected in the order total before confirmation.
- **SC-002**: 100% of attempts to apply an unrecognized or empty code
  are rejected with a clear message and leave the order total unchanged.
- **SC-003**: When a shopper applies a second valid code on the same
  checkout, the final total reflects only the most recently applied
  code's percentage off the original subtotal — never a stacked or
  compounded discount.
- **SC-004**: The automated test suite for this feature covers all three
  valid percentages plus at least one invalid-code path, and passes on
  every commit.

## Assumptions

- The exact discount code strings (e.g., `SAVE5`, `SAVE10`, `SAVE20`)
  are a configuration detail that can be decided during planning; the
  spec only fixes that there are three codes mapping to 5%, 10%, and
  20%.
- Discount codes in this first version are not time-limited, are not
  per-shopper, and have no usage cap. Adding expiry, per-user limits,
  or usage caps is out of scope for v1.
- Currency, taxes, and shipping handling are unchanged by this feature.
  The discount applies to the order subtotal as currently computed by
  the checkout flow.
- The checkout flow already identifies the acting shopper through the
  existing mechanism; no new authentication is introduced.
