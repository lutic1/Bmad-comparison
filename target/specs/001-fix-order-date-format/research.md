# Research: Fix Order Date Format

**Feature**: 001-fix-order-date-format
**Date**: 2026-05-18

## Findings

### Decision: ISO 8601 date format `YYYY-MM-DD`

**Decision**: Use `strftime("%Y-%m-%d")` everywhere `created_at` is serialized.

**Rationale**: ISO 8601 is the unambiguous, internationally standard date
format. The spec explicitly names it. The existing format string `%Y-%d-%m`
(year-day-month) is non-standard and produces incorrect output for any date
where day ≠ month.

**Alternatives considered**: No alternative formats are reasonable for a
REST API returning structured data. Returning a full `datetime` ISO string
(with time component) was considered but ruled out — the existing contract
returns a date-only string and changing the type would be a breaking change
outside this bug's scope.

---

### Decision: Fix all three call sites

**Decision**: Fix the format string in:
1. `src/api/routes/orders.py:77` — `create_order` response
2. `src/api/routes/orders.py:101` — `get_order` response
3. `src/api/routes/orders.py:127` — private `_format_created_at` helper
4. `src/api/utils/dates.py:5` — `format_order_date` utility

**Rationale**: All four sites contain the same wrong format string. A
partial fix would leave latent bugs. The utility function `format_order_date`
in `dates.py` is tested directly in `tests/test_dates.py` and must be
correct. The private helper `_format_created_at` in `orders.py` is currently
unused by the route handlers (they call `strftime` directly) but must also
be corrected for consistency.

**Alternatives considered**: Consolidating all call sites to use
`format_order_date` was considered but rejected — that is a refactor,
which violates Constitution VII (Change Discipline). Each site is fixed
in-place.

---

### Decision: Update test assertions, not test structure

**Decision**: Update the expected strings in `tests/test_dates.py` from
`"2025-07-03"` → `"2025-03-07"` and `"2024-31-12"` → `"2024-12-31"`.

**Rationale**: The test structure is correct — the tests exercise
`format_order_date` with known inputs. Only the expected output values are
wrong (they were written to match the buggy implementation). No new test
infrastructure is needed.

**Alternatives considered**: Deleting and rewriting the tests was
considered unnecessary — the existing test cases already use asymmetric
dates (March 7, December 31) that expose the bug, making them good
regression tests once the assertions are corrected.

---

## No NEEDS CLARIFICATION items

All decisions are fully resolved from codebase inspection. No external
research required.
