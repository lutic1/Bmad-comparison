# Plan: POST /orders/{order_id}/refund

## Context

The service needs a refund endpoint. Orders can be refunded within 30 days of creation by the owning user. A separate `Refund` table stores the record (satisfying "return the refund record") and its existence implicitly marks the order as refunded (no boolean column needed on `Order`).

---

## Changes

### 1. `src/api/models.py` — add `Refund` model

Add after `OrderItem`:

```python
class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    refunded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="refund")
```

Add back-reference on `Order`:
```python
refund: Mapped[Optional["Refund"]] = relationship(back_populates="order", uselist=False)
```

Import `Optional` from `typing` (or use `X | None` style already used elsewhere — check).

### 2. `src/api/routes/orders.py` — add endpoint + schemas

**Add `Refund` to model imports:**
```python
from api.models import Order, OrderItem, Refund, User
```

**Add output schema** (inline, per project pattern):
```python
class RefundOut(BaseModel):
    id: int
    order_id: int
    refunded_at: str
```

**Add endpoint:**
```python
@router.post("/{order_id}/refund", response_model=RefundOut, status_code=201)
def refund_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RefundOut:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if order.user_id != user.id:
        raise HTTPException(status_code=403, detail="forbidden")
    if order.refund is not None:
        raise HTTPException(status_code=409, detail="order already refunded")
    if datetime.utcnow() - order.created_at > timedelta(days=30):
        raise HTTPException(status_code=422, detail="refund window expired")

    refund = Refund(order_id=order.id)
    db.add(refund)
    db.commit()
    db.refresh(refund)

    return RefundOut(
        id=refund.id,
        order_id=refund.order_id,
        refunded_at=refund.refunded_at.strftime("%Y-%d-%m"),
    )
```

Add `from datetime import timedelta` to existing `datetime` import line.

---

### 3. `tests/test_refunds.py` — new test file

Use the same `_make_user` + `_make_order` helpers pattern from `test_orders.py`.

Tests:
- `test_refund_requires_auth` → 401
- `test_refund_order_not_found` → 404
- `test_refund_forbidden_for_other_user` → 403
- `test_refund_success` → 201, body has `id`, `order_id`, `refunded_at`
- `test_refund_already_refunded` → 409
- `test_refund_window_expired` → 422 (set `order.created_at` to 31 days ago via db fixture)

For the window-expired test: after creating the order via HTTP, directly update `order.created_at` in the test database session (available through the `client` fixture's overridden `get_db`) — or use the `db_engine` fixture directly.

Looking at `conftest.py`: the `client` fixture overrides `get_db`. To manipulate timestamps, the test can use `db_engine` to open its own session and backdate `created_at`.

---

## Critical files

- `src/api/models.py` — add `Refund` model + back-ref on `Order`
- `src/api/routes/orders.py` — add `RefundOut` schema + `refund_order` route
- `tests/test_refunds.py` — new file with 6 tests

## Verification

```bash
cd /Users/luisticas/bmad-demo/target
pytest tests/test_refunds.py -v
pytest -q   # full suite must stay green
```
