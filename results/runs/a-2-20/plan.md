# Plan: POST /orders/{order_id}/refund

## Context
The service has users and orders but no refund capability. This adds a refund endpoint that enforces ownership, a 30-day window, and idempotency protection (no double-refunds).

## Changes

### 1. `src/api/models.py` — add `refunded_at` to `Order`
```python
refunded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
```
No migration needed (CLAUDE.md: schema is recreated from `Base.metadata` at startup).

### 2. `src/api/routes/orders.py` — add `RefundOut` + endpoint

**New Pydantic model** (add after `OrderOut`):
```python
class RefundOut(BaseModel):
    order_id: int
    amount: int
    refunded_at: str
```

**New endpoint** (add after `get_order`):
```python
@router.post("/{order_id}/refund", response_model=RefundOut)
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
    if order.refunded_at is not None:
        raise HTTPException(status_code=409, detail="order already refunded")
    if datetime.utcnow() - order.created_at > timedelta(days=30):
        raise HTTPException(status_code=422, detail="refund window expired")
    order.refunded_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return RefundOut(
        order_id=order.id,
        amount=order.total,
        refunded_at=order.refunded_at.isoformat(),
    )
```

Add `from datetime import timedelta` to the existing import at the top of the file.

### 3. `tests/test_refunds.py` — new test file

Helpers reused from existing `test_orders.py` pattern (`_make_user`, `_make_order`).

Tests:
- `test_refund_requires_auth` → 401 (no header)
- `test_refund_order_not_found` → 404
- `test_refund_forbidden_for_other_user` → 403
- `test_refund_success` → 200, body contains `order_id`, `amount`, `refunded_at`
- `test_refund_already_refunded` → 409
- `test_refund_outside_30_day_window` → 422 (manipulates `order.created_at` via `db_engine` directly since `conftest.py` uses `StaticPool` — all sessions share the same connection, so direct DB writes are visible to the test client)

## Verification
```
pytest tests/test_refunds.py -v
pytest -q   # full suite must stay green
```

## Critical files
- `src/api/models.py`
- `src/api/routes/orders.py`
- `tests/test_refunds.py` (new)
- `tests/conftest.py` (read-only reference — `db_engine` fixture is already available)
