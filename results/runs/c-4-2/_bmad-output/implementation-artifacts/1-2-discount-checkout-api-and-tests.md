# Story 1.2: Discount Checkout API and Tests

Status: done

## Story

As an API consumer,
I want to optionally include a discount code when creating an order,
so that the discounted total is applied, persisted, and returned in the response.

## Context

**Depends on Story 1.1 being complete.** The `DiscountCode` model and the three new `Order` columns (`original_total`, `discount_code`, `discount_percentage`) must already exist in `models.py`, and the `db` fixture must exist in `tests/conftest.py`. This story touches `src/api/routes/orders.py` (extend schemas and route logic) and adds `tests/test_discounts.py` (all discount-specific tests). No other files change.

The service stores all money as **integer cents**. `_to_cents(dollars)` converts incoming floats once at the boundary. Discount math stays in integer arithmetic: `original_total * (100 - pct) // 100` (floor division — no `math`, no `round()`). The existing `OrderOut` is **manually constructed** (not via `from_attributes`) — new fields must be added to the constructor call, not just the Pydantic model.

## Acceptance Criteria

1. `OrderCreate` has `discount_code: str | None = None` (optional field, backward-compatible).
2. `OrderOut` has `original_total: int`, `discount_code: str | None`, `discount_percentage: int | None`.
3. `POST /orders` without `discount_code` returns `discount_code: null`, `discount_percentage: null`, `original_total == total` — all existing tests continue to pass unchanged.
4. `POST /orders` with an unknown code returns HTTP 400, detail `"discount code not found"`.
5. `POST /orders` with an inactive code (`is_active=False`) returns HTTP 400, detail `"discount code is not active"`.
6. `POST /orders` with an exhausted code (`times_used >= max_uses`, non-null) returns HTTP 400, detail `"discount code has been fully redeemed"`. Order is **not** created on any 400.
7. `POST /orders` with a valid code returns HTTP 201 with `total = floor(original_total * (100 - pct) / 100)`, correct `original_total`, `discount_code` (uppercased), `discount_percentage`.
8. After a successful discounted checkout, `DiscountCode.times_used` is incremented by 1 in the same transaction.
9. Code lookup is case-insensitive (`"save10"` resolves the same as `"SAVE10"`).
10. `GET /orders/{id}` returns all three new fields from persisted columns (no new logic — just the extended `OrderOut` constructor).
11. `pytest` passes with zero failures.

## Tasks / Subtasks

- [x] Update `src/api/routes/orders.py` (AC: 1–10)
  - [x] Add `DiscountCode` to the `from api.models import ...` line
  - [x] Add `discount_code: str | None = None` to `OrderCreate`
  - [x] Add `original_total: int`, `discount_code: str | None`, `discount_percentage: int | None` to `OrderOut`
  - [x] In `create_order`: capture `original_total` after the item-sum loop; add discount validation + math block before `db.commit()`; set all new `order.*` fields; increment `dc.times_used`
  - [x] Update `OrderOut(...)` constructor in `create_order` to include new fields
  - [x] Update `OrderOut(...)` constructor in `get_order` to include new fields
- [x] Create `tests/test_discounts.py` (AC: 1–11)
  - [x] Module-level `_seed_code(db, ...)` helper
  - [x] 11 test functions (see test matrix below)
- [x] Verify (AC: 11)
  - [x] Run `pytest` — must pass with zero failures

## Dev Notes

### Critical Conventions

- **`OrderOut` is manually constructed** — it does NOT use `from_attributes = True`. `OrderItemOut` does. These are different. Adding a field to `OrderOut` means adding it to the `OrderOut(...)` call in BOTH `create_order` and `get_order`. If you only update the Pydantic model, the fields will be `None` / missing.
- **Integer floor division for discount:** `original_total * (100 - dc.percentage) // 100`. No `math.floor`, no `round()`, no floats. Verification: 1001 cents × 95 // 100 = 950 ✓; 10000 × 90 // 100 = 9000 ✓.
- **Case-insensitive lookup:** `db.query(DiscountCode).filter(DiscountCode.code == payload.discount_code.upper()).one_or_none()`. Codes are stored uppercase by convention.
- **One DB session per request.** Use the `db: Session` already injected by `Depends(get_db)`. Do not open a second session or import the engine directly.
- **Transactional safety:** `dc.times_used += 1` and all `order.*` assignments happen before the single existing `db.commit()`. If the commit fails, neither persists.
- **Date format is `%Y-%d-%m`** (day and month swapped — NOT ISO 8601). Do not "fix" this. Copy the existing `strftime` call exactly.
- **No new third-party imports.** All needed symbols are already in `sqlalchemy`, `fastapi`, or stdlib.

### Discount validation block (inline in `create_order`, after item-sum loop)

```python
original_total = total  # cents, pre-discount

applied_code: str | None = None
applied_pct: int | None = None

if payload.discount_code:
    dc = db.query(DiscountCode).filter(
        DiscountCode.code == payload.discount_code.upper()
    ).one_or_none()
    if dc is None:
        raise HTTPException(status_code=400, detail="discount code not found")
    if not dc.is_active:
        raise HTTPException(status_code=400, detail="discount code is not active")
    if dc.max_uses is not None and dc.times_used >= dc.max_uses:
        raise HTTPException(status_code=400, detail="discount code has been fully redeemed")
    total = original_total * (100 - dc.percentage) // 100
    dc.times_used += 1
    applied_code = dc.code
    applied_pct = dc.percentage

order.total = total
order.original_total = original_total
order.discount_code = applied_code
order.discount_percentage = applied_pct
```

This block goes **after** the item-accumulation loop and **before** `db.commit()`. The existing `order.total = total` line is replaced by `order.total = total` inside this block.

### Test matrix (all 11 functions for `tests/test_discounts.py`)

| Function | What it checks |
|----------|---------------|
| `test_discount_applied_correct_total` | Valid 10% code → `total=9000`, `original_total=10000`, fields populated |
| `test_discount_times_used_incremented` | After checkout, `db.get(DiscountCode, dc.id).times_used == 1` |
| `test_discount_5pct_rounding` | 5% on 1001 cents → `total=950` (floor, not round) |
| `test_discount_20pct` | 20% code → correct total |
| `test_no_discount_code_backward_compat` | No `discount_code` key → 201, `discount_code: null`, `original_total == total` |
| `test_unknown_code_returns_400` | `"FAKE"` → 400, detail `"discount code not found"` |
| `test_inactive_code_returns_400` | `is_active=False` → 400, detail `"discount code is not active"` |
| `test_exhausted_single_use_code_returns_400` | `max_uses=1, times_used=1` → 400, detail `"has been fully redeemed"` |
| `test_case_insensitive_lookup` | Seed `"SAVE10"`, submit `"save10"` → 201 |
| `test_get_order_returns_discount_fields` | `GET /orders/{id}` after discounted POST → fields persist |
| `test_get_order_no_discount_fields_null` | `GET /orders/{id}` after plain POST → `discount_code: null`, `original_total == total` |

### `_seed_code` helper pattern

```python
from api.models import DiscountCode

def _seed_code(
    db,
    code: str = "SAVE10",
    percentage: int = 10,
    is_active: bool = True,
    max_uses: int | None = None,
    times_used: int = 0,
) -> DiscountCode:
    dc = DiscountCode(
        code=code,
        percentage=percentage,
        is_active=is_active,
        max_uses=max_uses,
        times_used=times_used,
    )
    db.add(dc)
    db.commit()
    db.refresh(dc)
    return dc
```

Tests that need both HTTP and DB access: `def test_foo(client, db)`. The `db` fixture added in Story 1.1 shares the same in-memory engine as `client` — seeded rows are immediately visible to the HTTP client.

### What NOT to do

- Do not change `tests/test_orders.py` — existing tests must pass without modification. The new nullable fields default to `null` on non-discounted orders, which does not affect current assertions.
- Do not extract a `_validate_discount_code` helper — it's one call site; inline is correct per CLAUDE.md.
- Do not add `from_attributes = True` to `OrderOut` — that changes existing serialization semantics.
- Do not change the date format.
- Do not add any new route file or router — all changes are in the existing `orders.py`.

### Project Structure Notes

- Two files change: `src/api/routes/orders.py` (extend), `tests/test_discounts.py` (new).
- No changes to `deps.py`, `main.py`, `users.py`, `conftest.py` (already updated in Story 1.1), or any other file.

### References

- Architecture: `_bmad-output/planning-artifacts/architecture/discount-codes-architecture.md` §5
- PRD FR-2 through FR-6: `_bmad-output/planning-artifacts/prds/prd-target-2026-05-19/prd.md` §4.2–4.3
- Existing route: `src/api/routes/orders.py`
- Existing tests: `tests/test_orders.py` (must not regress)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Imported `DiscountCode` in routes/orders.py
- Extended `OrderCreate` with optional `discount_code` field
- Extended `OrderOut` with `original_total`, `discount_code`, `discount_percentage`
- Added 15-line inline validation+math block in `create_order` (case-insensitive lookup, 3 validation checks, integer floor division)
- Updated both `OrderOut(...)` constructors (create_order and get_order) with new fields
- Created `tests/test_discounts.py` with 11 tests covering all FR-6 scenarios
- 22/22 tests pass (11 new + 11 existing); zero regressions

### File List

- src/api/routes/orders.py
- tests/test_discounts.py
