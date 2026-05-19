# Plan: POST /orders/{order_id}/refund

## Context
Add a refund endpoint to the existing orders router. It marks an order as refunded by adding a `refunded_at` timestamp column to `Order`, validates ownership and the 30-day window, and returns a `RefundOut` record. No new table needed — a nullable timestamp on `Order` is sufficient.

---

## Files to Modify

| File | Change |
|---|---|
| `src/api/models.py` | Add `refunded_at` nullable column to `Order` |
| `src/api/routes/orders.py` | Add `RefundOut` model + `refund_order` route |
| `tests/conftest.py` | Add `db` fixture for direct DB access in tests |
| `tests/test_orders.py` | Add refund tests |

---

## 1. `src/api/models.py`

Add to `Order` class:

```python
refunded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
```

Also add `from datetime import datetime` if not already at the top (it already is).

---

## 2. `src/api/routes/orders.py`

Add import at top:
```python
from datetime import timedelta
```

Add Pydantic response model (alongside existing models):
```python
class RefundOut(BaseModel):
    order_id: int
    refunded_at: str
```

Add route (after `get_order`, before `adjust_total`):
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
    cutoff = datetime.utcnow() - timedelta(days=30)
    if order.created_at < cutoff:
        raise HTTPException(status_code=400, detail="refund window expired")
    order.refunded_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return RefundOut(
        order_id=order.id,
        refunded_at=order.refunded_at.strftime("%Y-%d-%m"),
    )
```

---

## 3. `tests/conftest.py`

Add a `db` fixture so tests can directly manipulate DB state (needed for the 30-day window test):

```python
@pytest.fixture
def db(db_engine):
    TestingSessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
```

Because `StaticPool` shares one connection, changes committed via `db` are visible to the `client`'s sessions.

---

## 4. `tests/test_orders.py` — new tests

```python
def _make_order(client, user_id, sku="SKU", price=1.00):
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": [{"sku": sku, "quantity": 1, "unit_price": price}]},
    )
    assert resp.status_code == 201
    return resp.json()


def test_refund_requires_auth(client):
    user = _make_user(client, email="ra@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(f"/orders/{order['id']}/refund")
    assert resp.status_code == 401


def test_refund_order_not_found(client):
    user = _make_user(client, email="rnf@example.com")
    resp = client.post("/orders/99999/refund", headers={"X-User-Id": str(user["id"])})
    assert resp.status_code == 404


def test_refund_forbidden_for_other_user(client):
    owner = _make_user(client, email="rfo@example.com")
    other = _make_user(client, email="rfo2@example.com")
    order = _make_order(client, owner["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund", headers={"X-User-Id": str(other["id"])}
    )
    assert resp.status_code == 403


def test_refund_expired_window(client, db):
    from datetime import timedelta
    from api.models import Order
    user = _make_user(client, email="rew@example.com")
    order = _make_order(client, user["id"])
    # backdate created_at beyond 30 days
    db_order = db.get(Order, order["id"])
    db_order.created_at = datetime.utcnow() - timedelta(days=31)
    db.commit()
    resp = client.post(
        f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])}
    )
    assert resp.status_code == 400


def test_refund_already_refunded(client):
    user = _make_user(client, email="rar@example.com")
    order = _make_order(client, user["id"])
    headers = {"X-User-Id": str(user["id"])}
    client.post(f"/orders/{order['id']}/refund", headers=headers)
    resp = client.post(f"/orders/{order['id']}/refund", headers=headers)
    assert resp.status_code == 409


def test_refund_success(client):
    user = _make_user(client, email="rs@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund", headers={"X-User-Id": str(user["id"])}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["order_id"] == order["id"]
    assert "refunded_at" in body
```

Also add `from datetime import datetime` at the top of `test_orders.py` (needed for `test_refund_expired_window`).

---

## Verification

```bash
cd /Users/luisticas/bmad-demo/target
pytest tests/test_orders.py -v
```

All 6 new tests plus the 5 existing tests should pass.
