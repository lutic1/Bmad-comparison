# Feature Specification: Fix Order Date Format

**Feature Branch**: `001-fix-order-date-format`

**Created**: 2026-05-18

**Status**: Draft

**Input**: User description: "There's a bug in how order dates are formatted in the API response. Find it and fix it. Update tests as needed."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Correct Date in Order Response (Priority: P1)

An API consumer creates an order or retrieves an existing one. The `created_at`
field in the response should be a human-readable calendar date in standard
ISO 8601 format (YYYY-MM-DD). Currently it comes back with day and month swapped
(YYYY-DD-MM), making the date unreadable or ambiguous — for example, the 5th
of January is returned as `2026-05-01` instead of `2026-01-05`, which looks
like the 1st of May.

**Why this priority**: Incorrect date formatting corrupts information surfaced
to any consumer of this API — clients, downstream services, reports — and is
a data-correctness regression.

**Independent Test**: Create an order on a known calendar date (e.g., 18 May
2026) and assert the response contains `created_at: "2026-05-18"`. This can be
tested end-to-end against both the create and retrieve endpoints.

**Acceptance Scenarios**:

1. **Given** an order is created on 2026-05-18, **When** the create-order
   endpoint responds, **Then** `created_at` equals `"2026-05-18"`.
2. **Given** an existing order created on 2026-05-18, **When** the get-order
   endpoint responds, **Then** `created_at` equals `"2026-05-18"`.
3. **Given** an order created on the 1st of any month (day ≠ month),
   **When** either endpoint responds, **Then** the day and month are not
   transposed in `created_at`.

---

### Edge Cases

- What happens when day and month share the same numeric value (e.g., 2026-03-03)?
  The bug is invisible for such dates; tests must use dates where day ≠ month
  to expose the regression.
- What happens when the stored timestamp is at a month/day boundary near
  midnight UTC? The formatted string must still reflect the correct calendar
  date.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `created_at` field in every order API response MUST be
  formatted as `YYYY-MM-DD` (ISO 8601 date).
- **FR-002**: The create-order endpoint (`POST /orders`) MUST return
  `created_at` in `YYYY-MM-DD` format.
- **FR-003**: The get-order endpoint (`GET /orders/{id}`) MUST return
  `created_at` in `YYYY-MM-DD` format.
- **FR-004**: Any shared date-formatting utility used by order routes MUST
  produce `YYYY-MM-DD` output.
- **FR-005**: All existing tests that assert date format MUST be updated to
  expect the correct `YYYY-MM-DD` output, not the previously incorrect
  `YYYY-DD-MM` output.

### Key Entities

- **Order**: Has a `created_at` timestamp; the formatted representation of
  this field in API responses is the subject of this fix.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of order API responses return `created_at` as `YYYY-MM-DD`.
- **SC-002**: No test in the suite asserts a `YYYY-DD-MM`-formatted date.
- **SC-003**: All tests pass after the fix, including any tests updated to
  reflect the correct format.

## Assumptions

- The intended format is ISO 8601 (`YYYY-MM-DD`); no other format (e.g.,
  locale-specific or RFC 2822) has been specified.
- Only the `created_at` field on order responses is affected; other date
  fields in the API (e.g., on user resources) are out of scope for this fix.
- Existing stored data does not need migration — the bug is purely in the
  serialisation layer, not in how dates are persisted.
