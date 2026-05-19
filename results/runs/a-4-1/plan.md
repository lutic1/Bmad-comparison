# Plan: Percentage Discount Code at Checkout

## Context
Users need to apply discount codes (5%, 10%, or 20% off) when creating orders. There's no existing discount infrastructure. Discount codes must be stored persistently so tests can create and validate them.

## Files to Modify / Create

| File | Action |
|---|---|
| `src/api/models.py` | Add `DiscountCode` model; add two nullable columns to `Order` |
| `src/api/routes/orders.py` | Accept optional `discount_code` on create; apply discount; expose in response |
| `src/api/main.py` | Register the new discount-codes router |
| `src/api/routes/discount_codes.py` | **New** — `POST /discount-codes` endpoint |
| `tests/test_discount_codes.py` | **New** — all discount-related tests |

---

## Step 1 — `src/api/models.py`

Add `DiscountCode` model (after `OrderItem`):

```python
class DiscountCode(Base):
    __tablename__ = "discount_codes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    pct: Mapped[int] = mapped_column(Integer, nullable=False)  # 5, 10, or 20
```

Add two nullable columns to `Order` (after `created_at`):

```python
    discount_code: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    discount_pct: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
```

---

## Step 2 — New `src/api/routes/discount_codes.py`

```python
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from api.deps import get_db
from api.models import DiscountCode

router = APIRouter(prefix="/discount-codes", tags=["discount-codes"])

class DiscountCodeCreate(BaseModel):
    code: str
    pct: Literal[5, 10, 20]

class DiscountCodeRead(BaseModel):
    id: int
    code: str
    pct: int
    class Config:
        from_attributes = True

@router.post("", response_model=DiscountCodeRead, status_code=201)
def create_discount_code(payload: DiscountCodeCreate, db: Session = Depends(get_db)) -> DiscountCode:
    existing = db.query(DiscountCode).filter(DiscountCode.code == payload.code).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="discount code already exists")
    dc = DiscountCode(code=payload.code, pct=payload.pct)
    db.add(dc)
    db.commit()
    db.refresh(dc)
    return dc
```

---

## Step 3 — `src/api/main.py`

Add import and `include_router`:

```python
from api.routes import discount_codes, orders, users
# ...
app.include_router(discount_codes.router)
```

---

## Step 4 — `src/api/routes/orders.py`

**4a.** Add `DiscountCode` to import:
```python
from api.models import DiscountCode, Order, OrderItem, User
```

**4b.** Add optional field to `OrderCreate`:
```python
class OrderCreate(BaseModel):
    items: list[OrderItemIn]
    discount_code: str | None = None
```

**4c.** Add optional fields to `OrderOut`:
```python
class OrderOut(BaseModel):
    id: int
    user_id: int
    total: int
    created_at: str
    items: list[OrderItemOut]
    discount_code: str | None = None
    discount_pct: int | None = None
```

**4d.** In `create_order`, after the items loop and before `db.commit()`, insert:
```python
    if payload.discount_code is not None:
        dc = db.query(DiscountCode).filter(DiscountCode.code == payload.discount_code).one_or_none()
        if dc is None:
            raise HTTPException(status_code=400, detail="invalid discount code")
        total -= int(total * dc.pct / 100)
        order.discount_code = dc.code
        order.discount_pct = dc.pct

    order.total = total
```

**4e.** Update both `OrderOut(...)` constructions (in `create_order` and `get_order`) to include:
```python
        discount_code=order.discount_code,
        discount_pct=order.discount_pct,
```

---

## Step 5 — `tests/test_discount_codes.py`

Tests (one behaviour per test):

1. Create discount code → 201 with correct fields
2. Duplicate code → 409
3. Invalid pct (e.g. 15) → 422 (Pydantic)
4. Order with valid 10% code → total reduced correctly
5. Order with invalid code string → 400
6. Order without code → `discount_code` and `discount_pct` are `None`
7. GET order also returns discount fields
8. 5% discount truncates correctly (999 cents → 950)
9. 20% discount applies correctly (2000 cents → 1600)

---

## Rounding Note

Discount uses `int(total * pct / 100)` — integer truncation (floor). This is consistent with how `_to_cents` works and conventional "discount favors the merchant" semantics. The 5% test makes this explicit.

## Verification

```bash
cd /Users/luisticas/bmad-demo/target
pytest tests/test_discount_codes.py -v
pytest -q  # full suite must still pass
```
