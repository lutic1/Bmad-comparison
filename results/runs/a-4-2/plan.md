# Plan: Discount Code at Checkout

## Context
The service needs a way for users to apply a percentage discount when creating an order. Discounts are fixed tiers: 5%, 10%, or 20%, identified by short string codes. The discount reduces the order total at creation time and should be reflected in the response.

## Approach

### 1. `src/api/models.py` — add `discount_pct` column to `Order`

```python
discount_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

No migration needed — CLAUDE.md says wipe `app.db` between runs.

### 2. `src/api/routes/orders.py` — extend create-order endpoint

**Add constant mapping** (hardcoded, no DB table needed for 3 fixed codes):
```python
DISCOUNT_CODES: dict[str, int] = {"SAVE5": 5, "SAVE10": 10, "SAVE20": 20}
```

**Extend `OrderIn`** (request body):
```python
discount_code: str | None = None
```

**Extend `OrderOut`** (response):
```python
discount_pct: int | None
```

**In `POST /orders` handler**, after computing `total` from items:
```python
if body.discount_code is not None:
    pct = DISCOUNT_CODES.get(body.discount_code.upper())
    if pct is None:
        raise HTTPException(status_code=400, detail="Invalid discount code")
    order.discount_pct = pct
    order.total = max(0, round(order.total * (100 - pct) / 100))
```

### 3. `tests/test_orders.py` — add discount tests

Cases to cover:
- 5% code (`SAVE5`) reduces total correctly
- 10% code (`SAVE10`) reduces total correctly
- 20% code (`SAVE20`) reduces total correctly
- Invalid code returns 400
- No discount code still works (backward compat, `discount_pct` is `None`)
- Case-insensitive code matching (`save10` == `SAVE10`)

## Critical Files
- `src/api/models.py` — add `discount_pct` column
- `src/api/routes/orders.py` — add constant, extend Pydantic models, update handler
- `tests/test_orders.py` — new discount tests

## Reusable Patterns
- `_to_cents()` in `orders.py` — already used for float→cents; discount math stays in integer cents
- `adjust_total()` in `orders.py` — could be used but direct assignment is cleaner here
- `_make_user()` helper in `test_orders.py` — reuse for test setup
- `client` fixture in `conftest.py` — standard HTTP test harness

## Verification
1. Run `pytest tests/test_orders.py -v` — all existing + new tests must pass
2. Confirm discount total math: 1000 cents with 10% → 900 cents
3. Confirm `discount_pct: null` in response when no code supplied
4. Confirm 400 on unknown code
