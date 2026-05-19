# Plan: Percentage discount code at checkout

## Context

`POST /orders` accepts items and stores an integer-cents total. We want users to optionally include a discount code that applies 5%, 10%, or 20% off the subtotal. Valid codes are `SAVE5`, `SAVE10`, `SAVE20` (case-insensitive). The endpoint persists the discounted total — no schema change, no new abstraction, single call site. Per CLAUDE.md: stdlib only, every change ships with tests, no migration needed.

## Approach

- Add a module-level constant `DISCOUNT_CODES = {"SAVE5": 5, "SAVE10": 10, "SAVE20": 20}` in `src/api/routes/orders.py`.
- Add an optional `discount_code: str | None = None` field on `OrderCreate`.
- In `create_order`, after the line-item loop computes `total` and before `order.total = total`, validate and apply the discount.
- Use integer floor division: `discount_cents = (total * percent) // 100`, then `total -= discount_cents`. Avoids fractional cents.
- Invalid code → `HTTPException(400, "invalid discount code")`. Missing/empty code → no-op (existing behavior preserved).
- `OrderOut`, `get_order`, and the `Order` model are unchanged.

## Files to modify

- `src/api/routes/orders.py` — add constant, extend `OrderCreate`, apply discount inside `create_order`.
- `tests/test_orders.py` — add four tests using the existing `client` fixture and `_make_user` helper.

## Code sketch

In `src/api/routes/orders.py`, after `_to_cents`:

```python
DISCOUNT_CODES = {"SAVE5": 5, "SAVE10": 10, "SAVE20": 20}
```

Update `OrderCreate`:

```python
class OrderCreate(BaseModel):
    items: list[OrderItemIn]
    discount_code: str | None = None
```

In `create_order`, between the item loop and `order.total = total`:

```python
if payload.discount_code:
    code = payload.discount_code.upper()
    if code not in DISCOUNT_CODES:
        raise HTTPException(status_code=400, detail="invalid discount code")
    discount_cents = (total * DISCOUNT_CODES[code]) // 100
    total -= discount_cents

order.total = total
```

## Tests to add (`tests/test_orders.py`)

- `test_create_order_applies_valid_discount` — WIDGET ×2 @ 9.99 with `discount_code="SAVE10"` → `total == 1798` (1998 − 199 floor).
- `test_create_order_rejects_invalid_discount` — same items with `discount_code="BOGUS"` → 400, detail `"invalid discount code"`.
- `test_create_order_without_discount_unchanged` — same items, no `discount_code` key → `total == 1998` (regression guard).
- `test_create_order_discount_code_case_insensitive` — `discount_code="save20"` → `total == 1598` (1998 − 399 floor).

Each follows the existing pattern: `_make_user(...)` then `client.post("/orders", headers={"X-User-Id": str(user["id"])}, json={...})`.

## Verification

From repo root:

```
pytest tests/test_orders.py -v
```

Expect the 5 existing tests plus the 4 new tests all green. No other suites are touched.
