# Plan: POST /orders/{order_id}/refund

## Context
Add a refund endpoint to the existing FastAPI orders service. The endpoint must be authenticated, ownership-scoped, time-bounded (30 days), idempotency-safe (no double refunds), and return a refund record.

## Changes

### 1. `src/api/models.py`
Add a nullable `refunded_at` column to `Order`:
```python
refunded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
```

### 2. `src/api/routes/orders.py`
Add a `RefundOut` Pydantic response model:
```python
class RefundOut(BaseModel):
    order_id: int
    refunded_at: str
```

Add the route handler at the bottom of the existing routes:
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
    if order.refunded_at is not None:
        raise HTTPException(status_code=409, detail="order already refunded")
    age = datetime.utcnow() - order.created_at
    if age.days > 30:
        raise HTTPException(status_code=400, detail="refund window expired")
    order.refunded_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return RefundOut(
        order_id=order.id,
        refunded_at=order.refunded_at.strftime("%Y-%d-%m"),
    )
```

### 3. `tests/test_orders.py`
Add 6 new tests at the bottom of the existing file. Tests that need to manipulate `created_at` will use `db_engine` alongside `client` (both are already in conftest):

- `test_refund_requires_auth` — POST without header → 401
- `test_refund_order_not_found` — POST for nonexistent order_id → 404
- `test_refund_forbidden_for_other_user` — other user's order → 403
- `test_refund_success` — owner refunds within window → 200, returns `order_id` + `refunded_at`
- `test_refund_already_refunded` — second refund attempt → 409
- `test_refund_expired_window` — manipulate `created_at` to 31 days ago via `db_engine` session, then POST → 400

## Reused patterns
- `db.get(Order, order_id)` / ownership check — same as `get_order`
- `get_current_user` dependency — same as all protected routes
- `db.commit()` / `db.refresh()` — same as `create_order`
- `_make_user` helper in test file — reused in all new tests

## Verification
```bash
cd /Users/luisticas/bmad-demo/target
pytest tests/test_orders.py -v
```
All 11 tests (5 existing + 6 new) should pass.
