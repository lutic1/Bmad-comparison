# Data Model: Fix Order Date Format

**Feature**: 001-fix-order-date-format
**Date**: 2026-05-19

## Entities in Scope

### Order

No schema changes. Documented here for completeness.

| Field | Type | Notes |
|-------|------|-------|
| `id` | integer (PK) | auto-increment |
| `user_id` | integer (FK → users.id) | required |
| `total` | integer (cents) | required |
| `created_at` | datetime (naive UTC) | server-set default; never null |
| `items` | relationship | list of OrderItem |

**`created_at` serialization** (the bug and fix):

| State | Format string | Example output |
|-------|--------------|----------------|
| Buggy (current) | `%Y-%d-%m` | `"2026-19-05"` (wrong) |
| Fixed | `%Y-%m-%d` | `"2026-05-19"` (correct ISO 8601) |

The `OrderOut` Pydantic response model declares `created_at: str`. The route
handler constructs this string manually — no Pydantic serializer or validator
is involved. The fix is purely in the format string passed to `strftime`.

## Out of Scope

- `User.created_at` — not exposed by any endpoint; not changed.
- Timezone-awareness — left as naive UTC; out of scope for this fix.
