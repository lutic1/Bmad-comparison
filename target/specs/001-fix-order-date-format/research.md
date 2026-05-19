# Research: Fix Order Date Format

**Feature**: 001-fix-order-date-format
**Date**: 2026-05-19

## Bug Location

**Decision**: All date formatting happens inline in route handlers; no external
library or configuration is involved.

**Rationale**: The bug is a transposed format string in `strftime`. No research
into external systems or dependencies is needed.

**Alternatives considered**: None — cause is definitively identified from code
inspection.

---

## Finding 1: Swapped format codes in `strftime`

- **File**: `src/api/routes/orders.py`
- **Lines**: 77 (`create_order`), 101 (`get_order`), 127 (`_format_created_at`)
- **Current**: `order.created_at.strftime("%Y-%d-%m")`
- **Effect**: Produces `YYYY-DD-MM` (e.g., a date of 2026-05-19 becomes `"2026-19-05"`)
- **Fix**: Change to `strftime("%Y-%m-%d")` → produces ISO 8601 `YYYY-MM-DD`

## Finding 2: Dead-code helper carries the same bug

- `_format_created_at(dt)` at line 126-127 uses the same wrong format string
  and is never called. Fix it for consistency; do not remove (out of scope).

## Finding 3: Tests do not assert `created_at`

- `tests/test_orders.py` has no assertion on `created_at` in any test.
- `test_create_order_stores_cents` and `test_get_order_returns_owner` both
  receive the field in the response body but ignore it.
- Both tests must be updated with a format assertion; additionally a test
  using a date where day ≠ month SHOULD be added to prevent regression.

## Finding 4: No schema changes required

- `Order.created_at` is `Mapped[datetime]` with `default=datetime.utcnow`.
- `OrderOut.created_at` is typed `str` — the route manually serializes it.
- No migration, no model change, no Pydantic field change needed.

## Resolution Summary

| Unknown | Resolution |
|---------|------------|
| Root cause | Transposed `%d` and `%m` in three `strftime` calls |
| Scope | 2 production call sites + 1 dead-code helper + test assertions |
| Dependencies | None |
| Schema changes | None |
