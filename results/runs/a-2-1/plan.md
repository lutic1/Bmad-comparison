# Plan: Add POST /orders/{order_id}/refund endpoint

## Context

The service currently has order creation and retrieval but no refund capability. This adds a `POST /orders/{order_id}/refund` endpoint that authenticates the caller, validates ownership and refund eligibility (within 30 days, not already refunded), marks the order as refunded, and returns a refund record.

## Changes

### 1. `src/api/models.py` — Add refund fields to Order

Add two columns to the `Order` model:
- `refunded: Mapped[bool]` — `mapped_column(Boolean, default=False, nullable=False)`
- `refunded_at: Mapped[datetime | None]` — `mapped_column(DateTime, nullable=True)`

Import `Boolean` from `sqlalchemy`.

### 2. `src/api/routes/orders.py` — Add response model + route

**Add `RefundOut` Pydantic model** (after `OrderOut`):
```python
class RefundOut(BaseModel):
    order_id: int
    user_id: int
    refunded_at: str
```

**Add the route** (after `get_order`):
```python
@router.post("/{order_id}/refund", response_model=RefundOut, status_code=200)
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
    if (datetime.utcnow() - order.created_at).days > 30:
        raise HTTPException(status_code=400, detail="refund window expired")
    if order.refunded:
        raise HTTPException(status_code=400, detail="order already refunded")

    order.refunded = True
    order.refunded_at = datetime.utcnow()
    db.commit()
    db.refresh(order)

    return RefundOut(
        order_id=order.id,
        user_id=order.user_id,
        refunded_at=order.refunded_at.strftime("%Y-%d-%m"),
    )
```

### 3. `tests/test_orders.py` — Add refund tests

Add `_make_order` helper and the following tests:
- `test_refund_requires_auth` — POST without header → 401
- `test_refund_order_not_found` — POST for nonexistent order → 404
- `test_refund_forbidden_for_other_user` — POST by non-owner → 403
- `test_refund_succeeds_within_30_days` — POST within window → 200, check `order_id`, `user_id`, `refunded_at` present
- `test_refund_window_expired` — manually set `created_at` to 31 days ago via DB, POST → 400
- `test_refund_already_refunded` — refund twice → second call 400

For the expired-window test, access the SQLAlchemy session via `db_engine` fixture (already in conftest) to backdate `created_at`.

## Files to modify

- `src/api/models.py` — add `Boolean` import, `refunded`, `refunded_at` columns to `Order`
- `src/api/routes/orders.py` — add `RefundOut` model, `refund_order` route
- `tests/test_orders.py` — add refund test cases

## Verification

```bash
# From /Users/luisticas/bmad-demo/target
pytest tests/test_orders.py -v
```

All existing order tests should still pass; new refund tests should pass.
