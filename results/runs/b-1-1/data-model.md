# Data Model: Fix Order Date Format

**Feature**: `001-fix-order-date-format`
**Date**: 2026-05-18

## Summary

No schema changes are required. The bug is entirely in the serialisation
layer: the `created_at` column is stored correctly as a `DateTime` in SQLite;
only the string representation returned in API responses is wrong.

---

## Affected Entity: Order

| Field | DB Type | Stored correctly? | API representation (before fix) | API representation (after fix) |
|-------|---------|-------------------|----------------------------------|--------------------------------|
| `created_at` | `DateTime` | ✅ Yes | `YYYY-DD-MM` (e.g., `"2026-18-05"`) | `YYYY-MM-DD` (e.g., `"2026-05-18"`) |

All other `Order` fields are unaffected.

---

## Related Utility

`src/api/utils/dates.py` — `format_order_date(dt: datetime) -> str`

This helper exists but is not used by the route handlers (they call
`strftime` inline). The fix must be applied in all four locations listed
in `research.md`; using the shared helper in the routes is an option but
is out of scope per the constitution's refactoring principle (VII).
