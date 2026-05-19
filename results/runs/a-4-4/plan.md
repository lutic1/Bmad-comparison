# Discount codes at checkout

## Context

The order-creation endpoint (`POST /orders`) currently computes a total by
summing `unit_price_cents * quantity` across items, with no notion of
promotions. We want users to be able to pass a discount code in the
checkout payload and have a fixed-percentage discount (5%, 10%, or 20%)
applied to the order total. The code used and the discount amount should
be persisted on the order so receipts (`GET /orders/{id}`) show the
breakdown.

Per `CLAUDE.md`: keep it small, no new dependencies, no abstractions for
a single call site, no migrations needed (operator wipes `app.db`).

## Approach

A hardcoded mapping of three codes to their percentages lives in
`src/api/routes/orders.py`. `OrderCreate` gains an optional
`discount_code`. `create_order` looks the code up, computes the
discount in integer cents (`subtotal * pct // 100`), stores the code and
amount on the order, and sets `total = subtotal - discount`. `OrderOut`
exposes `subtotal`, `discount_code`, and `discount_amount` so the
response makes the math obvious.

Codes: `SAVE5` (5%), `SAVE10` (10%), `SAVE20` (20%). Case-sensitive
match — matches the simplest reading and avoids hidden normalization.

## Changes

### `src/api/models.py` — `Order`
Add two nullable/zero-default columns:
- `discount_code: Mapped[str | None] = mapped_column(String(32), nullable=True)`
- `discount_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`

`total` continues to be the final (post-discount) amount in cents; this
preserves the existing semantics of `Order.total` used by
`adjust_total` / `add_item_inline`.

### `src/api/routes/orders.py`
1. Module-level constant:
   ```python
   DISCOUNT_CODES: dict[str, int] = {"SAVE5": 5, "SAVE10": 10, "SAVE20": 20}
   ```
2. `OrderCreate`: add `discount_code: str | None = None`.
3. `OrderOut`: add `subtotal: int`, `discount_code: str | None`,
   `discount_amount: int`.
4. In `create_order`:
   - After computing `subtotal` (current `total` loop), if
     `payload.discount_code` is set:
     - Reject with `HTTPException(400, "invalid discount code")` if not
       in `DISCOUNT_CODES`.
     - `discount_amount = subtotal * DISCOUNT_CODES[code] // 100`
     - Store `order.discount_code = code`, `order.discount_amount = discount_amount`
   - `order.total = subtotal - discount_amount`
5. `OrderOut` construction in both `create_order` and `get_order`
   includes the new fields (subtotal = `order.total + order.discount_amount`).

No new utility/helper file — the lookup is three lines at one call site.

## Tests — `tests/test_orders.py`

Follow existing patterns (`_make_user` helper, `client` fixture,
`X-User-Id` header). Add:

- `test_create_order_with_save5_applies_5_percent` — items totaling 1000
  cents + `SAVE5` → total 950, discount_amount 50.
- `test_create_order_with_save10_applies_10_percent` — 2000 cents +
  `SAVE10` → total 1800, discount_amount 200.
- `test_create_order_with_save20_applies_20_percent` — 1000 cents +
  `SAVE20` → total 800, discount_amount 200.
- `test_create_order_invalid_discount_code_rejected` — `BOGUS` → 400.
- `test_create_order_no_discount_code_unchanged` — omitted code →
  `discount_code` is `None`, `discount_amount` is 0, total equals
  subtotal (regression guard for existing behaviour).
- `test_get_order_returns_discount_fields` — `GET /orders/{id}` after a
  discounted create returns the same `discount_code` /
  `discount_amount` / `subtotal`.

## Critical files

- `src/api/models.py` — add two columns on `Order`.
- `src/api/routes/orders.py` — code map, schema fields, discount logic
  in `create_order`, response shape in both routes.
- `tests/test_orders.py` — add six tests above.

## Verification

1. `pytest` from repo root → all tests pass (existing + new).
2. Spot-check manually:
   - `uvicorn api.main:app --reload` (operator will wipe `app.db` first).
   - `POST /users` to create a user, then `POST /orders` with header
     `X-User-Id: 1` and body
     `{"items":[{"sku":"A","quantity":1,"unit_price":10.00}], "discount_code":"SAVE10"}`
     → response shows `subtotal: 1000`, `discount_amount: 100`,
     `total: 900`, `discount_code: "SAVE10"`.
   - Same request with `"discount_code":"NOPE"` → 400.
