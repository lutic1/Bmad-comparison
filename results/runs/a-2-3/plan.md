# Plan: POST /orders/{order_id}/refund

## Context
The service needs a refund endpoint so users can request refunds on their own orders. Refunds must be gated by ownership, a 30-day window, and idempotency (no double-refunds).

## Changes

### 1. `src/api/models.py` — Add two columns to `Order`
Add imports for `Boolean` from sqlalchemy, and two new fields:
```python
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
...
class Order(Base):
    ...
    refunded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime, default=None, nullable=True)
```

### 2. `src/api/routes/orders.py` — Add response model + route

**New Pydantic model** (after `OrderOut`):
```python
class RefundOut(BaseModel):
    order_id: int
    refunded_at: str
```

**New route** (after `get_order`):
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
    if order.refunded:
        raise HTTPException(status_code=409, detail="order already refunded")
    now = datetime.utcnow()
    if (now - order.created_at) > timedelta(days=30):
        raise HTTPException(status_code=400, detail="refund window has expired")
    order.refunded = True
    order.refunded_at = now
    db.commit()
    db.refresh(order)
    return RefundOut(
        order_id=order.id,
        refunded_at=order.refunded_at.strftime("%Y-%d-%m"),
    )
```

Also add `timedelta` to the import: `from datetime import datetime, timedelta`.

### 3. `tests/test_orders.py` — Add 6 new tests

- `test_refund_requires_auth` → 401 (no X-User-Id header)
- `test_refund_order_not_found` → 404
- `test_refund_forbidden_for_other_user` → 403
- `test_refund_success` → 201, returns `order_id` + `refunded_at`
- `test_refund_already_refunded` → 409
- `test_refund_outside_30_days` → 400 (backdate `order.created_at` to 31 days ago via db session in test)

For the 30-day test, the test will need direct DB access to backdate `created_at`. The `client` fixture already exposes the overridden `get_db`; tests can call `next(override_get_db())` to get a session, update the order's `created_at`, and commit before calling the endpoint.

## Files modified
- `src/api/models.py`
- `src/api/routes/orders.py`
- `tests/test_orders.py`

## Verification
```bash
pytest tests/test_orders.py -v
```
All existing tests must continue to pass; 6 new tests must pass.
