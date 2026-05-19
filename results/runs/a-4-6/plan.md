# Add percentage discount codes at checkout

## Context

The orders service (`POST /orders` in `src/api/routes/orders.py`) currently sums
line items into an integer-cent total with no notion of discounts. The user
wants customers to be able to apply a percentage discount code at checkout,
limited to three tiers: 5%, 10%, and 20%.

There is no cart / separate checkout phase — order creation *is* checkout, so
the discount is applied inline during `create_order`.

## Approach

A small whitelist of discount codes lives in `routes/orders.py` as a constant
dict. `OrderCreate` gains an optional `discount_code`. During creation, we
total items as today, then (if a code is supplied) validate it, compute the
discount in cents, and subtract from the total. The applied code and the
discount amount are persisted on the `Order` row so they round-trip via
`GET /orders/{id}`.

Per `CLAUDE.md`: adding columns is fine — the operator wipes `app.db` between
runs, so no migration is needed.

## Files to change

### `src/api/models.py`
Add two columns to `Order`:
- `discount_code: Mapped[str | None] = mapped_column(String(32), nullable=True)`
- `discount_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`

### `src/api/routes/orders.py`

1. Module-level constant:
   ```python
   DISCOUNT_CODES: dict[str, int] = {"SAVE5": 5, "SAVE10": 10, "SAVE20": 20}
   ```
   (Percent values, not fractions. Codes are matched case-sensitively.)

2. Extend `OrderCreate`:
   ```python
   discount_code: str | None = None
   ```

3. Extend `OrderOut` to echo back applied discount info:
   ```python
   discount_code: str | None = None
   discount_cents: int = 0
   ```

4. In `create_order` — after the item-totaling loop, before `order.total = total`:
   - If `payload.discount_code` is set and not in `DISCOUNT_CODES` →
     `HTTPException(status_code=400, detail="invalid discount code")`.
   - If valid: `discount_cents = int(round(total * pct / 100))`, then
     `total -= discount_cents`, and store `order.discount_code` /
     `order.discount_cents`. Reuse the existing `_to_cents`-style rounding
     idiom (`int(round(...))`) for consistency.

5. Update both `OrderOut(...)` constructions (in `create_order` and
   `get_order`) to pass through `discount_code` and `discount_cents`.

### `tests/test_orders.py`
Add tests covering:
- Each tier reduces total correctly: `SAVE5` on a $10.00 item → total 950,
  `discount_cents` 50; `SAVE10` → 900/100; `SAVE20` → 800/200.
- Discount rounding: e.g. `SAVE10` on a 999¢ item → discount 100, total 899
  (verifies `int(round(...))` behavior).
- Unknown code (`"BOGUS"`) → 400 with `"invalid discount code"`.
- Omitted / `None` discount_code → no discount applied, `discount_cents == 0`,
  `discount_code is None`.
- `GET /orders/{id}` round-trips `discount_code` and `discount_cents`.

## What is intentionally out of scope

- No usage limits / expiry / per-user tracking — codes are stateless constants.
- No admin endpoint to manage codes — edit the dict in source.
- No stacking; at most one code per order (the API only accepts one).
- No case-insensitive matching — keep validation tight; can be relaxed later.

## Verification

1. `pytest` — full suite green, new tests pass.
2. Manual sanity check via the test client (optional):
   `POST /orders` with `{"items": [...], "discount_code": "SAVE10"}` and
   confirm response `total` is reduced and `discount_cents` is set; `GET` the
   same order and confirm the fields round-trip.
