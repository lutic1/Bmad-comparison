# Research: Fix Order Date Format

**Feature**: `001-fix-order-date-format`
**Date**: 2026-05-18

## Investigation Findings

### Decision: Correct date format is `%Y-%m-%d` (ISO 8601)

**Rationale**: The Python `strftime` directive `%m` is month and `%d` is
day-of-month. The format string `"%Y-%d-%m"` currently in use produces
`YYYY-DD-MM` (e.g., 18 May 2026 → `"2026-18-05"`), which transposes day and
month. The correct ISO 8601 short date format is `"%Y-%m-%d"`, producing
`YYYY-MM-DD` (e.g., `"2026-05-18"`).

**Alternatives considered**:
- RFC 2822 / locale-specific formats — rejected; spec calls for ISO 8601,
  which is the unambiguous standard for machine-readable dates in APIs.
- Delegating formatting to Pydantic (native `datetime` field) — would work
  but changes the response shape; spec does not request that change, and
  the existing `str` field is intentional.

---

### Bug locations (all stemming from the same typo)

| File | Line(s) | Current | Correct |
|------|---------|---------|---------|
| `src/api/utils/dates.py` | 5 | `"%Y-%d-%m"` | `"%Y-%m-%d"` |
| `src/api/routes/orders.py` | 77 | `"%Y-%d-%m"` | `"%Y-%m-%d"` |
| `src/api/routes/orders.py` | 101 | `"%Y-%d-%m"` | `"%Y-%m-%d"` |
| `src/api/routes/orders.py` | 127 (`_format_created_at`) | `"%Y-%d-%m"` | `"%Y-%m-%d"` |

---

### Tests requiring correction

`tests/test_dates.py` asserts the *buggy* output:

```python
# test_format_order_date_basic  — expects "2025-07-03" (YYYY-DD-MM)
# test_format_order_date_end_of_year — expects "2024-31-12" (YYYY-DD-MM)
```

Both assertions must be inverted to expect the correct `YYYY-MM-DD` values:
- `datetime(2025, 3, 7)` → `"2025-03-07"`
- `datetime(2024, 12, 31)` → `"2024-12-31"`

`tests/test_orders.py` does not currently assert `created_at` format. Two
new tests should be added to lock in the correct format for the `POST /orders`
and `GET /orders/{id}` endpoints.

---

### No NEEDS CLARIFICATION items

The codebase was read directly; all ambiguities are resolved by code
inspection. No external research was required.
