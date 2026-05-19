# Feature Specification: Fix Order Date Format

**Feature Branch**: `001-fix-order-date-format`

**Created**: 2026-05-18

**Status**: Draft

**Input**: User description: "There's a bug in how order dates are formatted in the API response. Find it and fix it. Update tests as needed."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Correct Date Format in Order Responses (Priority: P1)

An API consumer creates or retrieves an order and expects the `created_at`
field in the response to follow the ISO 8601 date format (YYYY-MM-DD). Due
to a transposed format string, the day and month positions are currently
swapped, so a date of March 7 is returned as `2025-07-03` instead of
`2025-03-07`.

**Why this priority**: Incorrect dates in API responses cause data
integrity failures for any consumer that parses or displays order dates —
this is a correctness bug with no acceptable workaround.

**Independent Test**: Can be fully tested by creating an order for a known
date and asserting the `created_at` field in the response matches
`YYYY-MM-DD` order (year, then month, then day).

**Acceptance Scenarios**:

1. **Given** an order created on March 7 2025, **When** the create-order
   endpoint is called, **Then** the response `created_at` is `"2025-03-07"`.
2. **Given** an existing order with a December 31 date, **When** the
   get-order endpoint is called, **Then** the response `created_at` is
   `"2024-12-31"` (not `"2024-31-12"`).
3. **Given** the date formatting utility function, **When** it is called
   with any date, **Then** it returns the date as `YYYY-MM-DD`.

---

### Edge Cases

- What happens when the day and month share the same value (e.g., May 5)?
  The bug is invisible in this case; the fix must still be verified with
  asymmetric dates.
- Dates at year boundaries (December 31, January 1) must format correctly.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The order API response `created_at` field MUST be formatted
  as `YYYY-MM-DD` (year, then month, then day).
- **FR-002**: The date formatting logic MUST be consistent across all order
  endpoints that return `created_at`.
- **FR-003**: The date formatting utility function MUST produce `YYYY-MM-DD`
  output for any valid datetime input.
- **FR-004**: Existing tests that assert the incorrect format MUST be
  updated to assert the correct `YYYY-MM-DD` format.

### Key Entities

- **Order**: Has a `created_at` datetime field that is serialized to a
  string in API responses.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All order API responses return `created_at` in `YYYY-MM-DD`
  format for any date where day ≠ month.
- **SC-002**: The date formatting utility function passes all tests with
  correct `YYYY-MM-DD` assertions.
- **SC-003**: No existing passing tests are broken by the change; all
  previously-incorrect date assertions are updated to correct values.

## Assumptions

- The intended format is ISO 8601 (`YYYY-MM-DD`); no other format was
  specified or is in use elsewhere.
- Timezone handling is out of scope — the existing behavior (naive datetime,
  date-only string) is preserved.
- Only `created_at` is affected; no other date fields exist on orders.
