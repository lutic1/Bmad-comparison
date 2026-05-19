# Feature Specification: Fix Order Date Format

**Feature Branch**: `001-fix-order-date-format`

**Created**: 2026-05-19

**Status**: Draft

**Input**: User description: "There's a bug in how order dates are formatted in the API response. Find it and fix it. Update tests as needed."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Correct date format in order responses (Priority: P1)

An API consumer fetching a single order or listing all orders receives the
`created_at` field in a standard, unambiguous date format (YYYY-MM-DD), so
dates can be parsed reliably without guessing field order.

**Why this priority**: The current format (`YYYY-DD-MM`) is ambiguous and
incorrect — consumers who parse it as ISO 8601 will get wrong dates, which
can cause downstream data errors (e.g., incorrect sorting, display, or
business logic).

**Independent Test**: Call GET /orders and GET /orders/{id}; assert the
`created_at` value in each response matches the pattern `YYYY-MM-DD` (e.g.,
`2026-05-19`), and that the year, month, and day values are correct.

**Acceptance Scenarios**:

1. **Given** an existing order created on 2026-05-19, **When** a consumer
   calls GET /orders, **Then** the response includes `"created_at": "2026-05-19"`.

2. **Given** an existing order created on 2026-05-19, **When** a consumer
   calls GET /orders/{id}, **Then** the response includes
   `"created_at": "2026-05-19"`.

3. **Given** the day and month differ (e.g., order created on 2026-01-07),
   **When** a consumer fetches that order, **Then** `created_at` is
   `"2026-01-07"` — not `"2026-07-01"`.

---

### Edge Cases

- What happens when `created_at` is not set (null/missing)? — Not applicable;
  the field has a server-set default and is always present.
- Do both the list endpoint and the single-order endpoint return the same
  format? — Yes; both MUST be consistent.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `created_at` field in every order API response MUST be
  formatted as ISO 8601 date (`YYYY-MM-DD`), with year first, then month,
  then day.
- **FR-002**: Both the list-orders endpoint and the get-order endpoint MUST
  return `created_at` in the same format.
- **FR-003**: Existing tests for order endpoints MUST be updated to assert
  that `created_at` matches the correct `YYYY-MM-DD` format.
- **FR-004**: No other fields in the order response MUST be changed.

### Key Entities

- **Order**: Has a `created_at` date field that records when the order was
  placed. This field is always set by the system (not user-supplied).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of order API responses return `created_at` in `YYYY-MM-DD`
  format with correct field ordering (year-month-day).
- **SC-002**: The test suite includes at least one assertion per order endpoint
  that validates the `created_at` format and value correctness.
- **SC-003**: No existing passing tests regress after the fix is applied.

## Assumptions

- The fix is limited to the `created_at` field on the Order resource; no
  other date fields are in scope.
- The desired output format is ISO 8601 date-only (`YYYY-MM-DD`).
- Both order endpoints (list and detail) are in scope.
- Timezone handling is out of scope; the existing naive UTC datetime default
  is acceptable for this fix.
