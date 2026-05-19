# Plan: Add `POST /orders/{order_id}/refund`

## Context

The service has no refund capability. Orders need to be markable as refunded, restricted to the order owner, and only within 30 days of creation. The result should be a returned "refund record" — implemented as a synthetic response constructed from a new `refunded_at` column on `Order` (no separate table needed).

---

## Files to Modify

1. `src/api/models.py` — add `refunded_at` column to `Order`
2. `src/api/routes/orders.py` — add `RefundOut` model + endpoint
3. `tests/test_orders.py` — add 6 tests

---

## Changes

### 1. `src/api/models.py`

Add one nullable column to `Order`, after `created_at`:

```python
refunded_at: Mapped[datetime | None] = mapped_column(
    DateTime, nullable=True, default=None
)
```

No migration needed — `Base.metadata.create_all()` picks it up at startup and in test fixtures.

---

### 2. `src/api/routes/orders.py`

**Import:** add `timedelta` to the existing `from datetime import datetime` line.

**New response model** (add after `OrderOut`):

```python
class RefundOut(BaseModel):
    order_id: int
    refunded_at: str
```

**New endpoint** (add after `get_order`, before the helper functions):

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
    if datetime.utcnow() - order.created_at > timedelta(days=30):
        raise HTTPException(status_code=422, detail="order is outside the refund window")
    if order.refunded_at is not None:
        raise HTTPException(status_code=409, detail="order already refunded")
    order.refunded_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return RefundOut(
        order_id=order.id,
        refunded_at=order.refunded_at.strftime("%Y-%d-%m"),
    )
```

Guard order: 404 → 403 → 422 → 409. Don't leak existence to unauthorized users.

`strftime("%Y-%d-%m")` matches the existing project date format (day before month, per `_format_created_at` and `test_dates.py`).

---

### 3. `tests/test_orders.py`

Add a `_make_order` helper (mirrors existing `_make_user` pattern):

```python
def _make_order(client, user_id, sku="SKU-1", quantity=1, unit_price=10.00):
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": [{"sku": sku, "quantity": quantity, "unit_price": unit_price}]},
    )
    assert resp.status_code == 201
    return resp.json()
```

**Six tests to add:**

| Test | Scenario | Expected |
|---|---|---|
| `test_refund_success` | valid owner, recent order | 201, body has `order_id` + `refunded_at` |
| `test_refund_requires_auth` | no X-User-Id | 401 |
| `test_refund_not_found` | order_id=99999 | 404 |
| `test_refund_forbidden` | different user | 403 |
| `test_refund_expired_window` | created_at backdated 31 days | 422 |
| `test_refund_already_refunded` | refund called twice | 409 on second call |

For `test_refund_expired_window`: use both `client` and `db_engine` fixtures. Because `client` depends on `db_engine` and both are function-scoped, pytest shares the same instance. Open a second `sessionmaker(bind=db_engine)` session to set `order.created_at = datetime.utcnow() - timedelta(days=31)` and commit — `StaticPool` ensures both sessions see the same in-memory DB.

---

## Verification

```bash
# Run only the order tests
cd /Users/luisticas/bmad-demo/target && python -m pytest tests/test_orders.py -v
```

All 11 tests (5 existing + 6 new) should pass. Confirm the 6 new tests cover: 201 success, 401, 404, 403, 422, 409.
