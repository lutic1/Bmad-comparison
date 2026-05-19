# Plan: Discount Code Feature

## Context

Add optional percentage discount codes to order creation (`POST /orders`). Valid codes map to 5%, 10%, or 20% off the order total. The applied code is persisted on the order and returned in both POST and GET responses.

## Files to Modify

1. `src/api/models.py`
2. `src/api/routes/orders.py`
3. `tests/test_orders.py`

---

## 1. `src/api/models.py`

Add nullable `discount_code` column to `Order` after `total`:

```python
discount_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
```

`String` is already imported; no other changes needed.

---

## 2. `src/api/routes/orders.py`

**Add constant** after `_to_cents`, before the Pydantic models:

```python
DISCOUNT_CODES: dict[str, int] = {"SAVE5": 5, "SAVE10": 10, "SAVE20": 20}
```

**Update `OrderCreate`** — add optional field:

```python
class OrderCreate(BaseModel):
    items: list[OrderItemIn]
    discount_code: str | None = None
```

**Update `OrderOut`** — add `discount_code` after `total`:

```python
class OrderOut(BaseModel):
    id: int
    user_id: int
    total: int
    discount_code: str | None
    created_at: str
    items: list[OrderItemOut]
```

**Update `create_order`** — add validation before DB flush, apply discount after computing total, persist code:

```python
# After empty-items guard, before db.flush():
if payload.discount_code is not None and payload.discount_code not in DISCOUNT_CODES:
    raise HTTPException(status_code=400, detail="invalid discount code")

# After total is computed (end of for loop), before order.total = total:
if payload.discount_code is not None:
    pct = DISCOUNT_CODES[payload.discount_code]
    discount_amount = int(round(total * pct / 100))
    total = total - discount_amount

order.total = total
order.discount_code = payload.discount_code

# Add discount_code to OrderOut(...) constructor call:
return OrderOut(
    id=order.id,
    user_id=order.user_id,
    total=order.total,
    discount_code=order.discount_code,
    created_at=order.created_at.strftime("%Y-%d-%m"),
    items=[...],
)
```

**Update `get_order`** — add `discount_code=order.discount_code` to the `OrderOut(...)` constructor call.

---

## 3. `tests/test_orders.py`

Add 6 tests after the existing 5:

| Test | Scenario | Expected |
|------|----------|----------|
| `test_create_order_no_discount_code` | No code supplied | total=1998, discount_code=None |
| `test_create_order_discount_save5` | SAVE5 on 1998 cents | total=1898 (−100) |
| `test_create_order_discount_save10` | SAVE10 on 1998 cents | total=1798 (−200) |
| `test_create_order_discount_save20` | SAVE20 on 1998 cents | total=1598 (−400) |
| `test_create_order_invalid_discount_code` | FAKE99 | 400 |
| `test_get_order_returns_discount_code` | GET after POST with SAVE10 | discount_code="SAVE10" |

**Discount arithmetic** (base: 2×$9.99 = 1998 cents):
- SAVE5: `int(round(1998×5/100))` = `int(round(99.9))` = 100 → 1898
- SAVE10: `int(round(1998×10/100))` = `int(round(199.8))` = 200 → 1798
- SAVE20: `int(round(1998×20/100))` = `int(round(399.6))` = 400 → 1598

---

## Verification

```bash
cd /Users/luisticas/bmad-demo/target
pytest tests/test_orders.py -v
```

All 11 order tests (5 existing + 6 new) should pass. The `db_engine` fixture calls `Base.metadata.create_all` so the new column is present in each test's in-memory DB automatically.
