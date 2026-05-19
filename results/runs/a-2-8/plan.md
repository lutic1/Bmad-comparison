# Add `POST /orders/{order_id}/refund`

## Context

The orders API currently supports create and fetch, but has no way to refund an order. We need an authenticated endpoint that lets the order's owner refund within 30 days of creation, marks the order as refunded, and returns the refund record. No `Refund` model or `refunded_at` field exists yet.

Design choice: rather than introduce a separate `Refund` table for a single use case, we add a single nullable `refunded_at` column to `Order`. The column doubles as the "is refunded?" flag and the timestamp — this matches the project's "no abstractions for a single call site" rule and the "no migrations, operator wipes app.db" workflow.

## Changes

### 1. `src/api/models.py` — add `refunded_at` to `Order`

Add one nullable column to `Order` (after `created_at` at line 31-33, before the `user` relationship at line 35):

```python
    refunded_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None
    )
```

No new imports needed — `datetime` and `DateTime` already imported.

### 2. `src/api/routes/orders.py` — add refund endpoint

**Update import** at line 1:

```python
from datetime import datetime, timedelta
```

**Add module-level constant** near `_to_cents` (line 13):

```python
REFUND_WINDOW = timedelta(days=30)
```

**Add response schema** after `OrderOut` (line 41):

```python
class RefundOut(BaseModel):
    order_id: int
    amount: int  # cents
    refunded_at: str
```

**Add handler** after `get_order` (line 106), before `adjust_total`:

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
        raise HTTPException(status_code=400, detail="order already refunded")
    if datetime.utcnow() - order.created_at > REFUND_WINDOW:
        raise HTTPException(status_code=400, detail="refund window expired")

    order.refunded_at = datetime.utcnow()
    db.commit()
    db.refresh(order)

    return RefundOut(
        order_id=order.id,
        amount=order.total,
        refunded_at=order.refunded_at.strftime("%Y-%d-%m"),
    )
```

Notes:
- Check order: existence → ownership → already-refunded → window. Ownership before "already refunded" so we don't leak refund state to non-owners.
- Use `datetime.utcnow()` (naive UTC) to match `created_at` (`default=datetime.utcnow` in models). Mixing tz-aware would break the `timedelta` math.
- Use `%Y-%d-%m` for `refunded_at` formatting to match the existing (quirky) format used by `OrderOut.created_at` at line 77/101 — don't refactor unrelated quirks.
- No request body — full refund of `order.total`. No `RefundCreate` schema.
- Router prefix `/orders` is already set at line 10; the path `/{order_id}/refund` produces `POST /orders/{order_id}/refund`. Already wired into `main.py`.

### 3. `tests/test_orders.py` — append six tests

Use the existing `_make_user` helper and `client` fixture. For the expired-window test, mutate `created_at` directly via a session bound to `db_engine` (the `StaticPool` in-memory SQLite means a separate session sees the same data).

```python
def test_refund_requires_auth(client):
    _make_user(client)
    resp = client.post("/orders/1/refund")
    assert resp.status_code == 401


def test_refund_order_not_found(client):
    user = _make_user(client, email="missing@example.com")
    resp = client.post(
        "/orders/999/refund", headers={"X-User-Id": str(user["id"])}
    )
    assert resp.status_code == 404


def test_refund_forbidden_for_other_user(client):
    owner = _make_user(client, email="rowner@example.com")
    other = _make_user(client, email="rother@example.com")
    created = client.post(
        "/orders",
        headers={"X-User-Id": str(owner["id"])},
        json={"items": [{"sku": "X", "quantity": 1, "unit_price": 1.00}]},
    ).json()
    resp = client.post(
        f"/orders/{created['id']}/refund",
        headers={"X-User-Id": str(other["id"])},
    )
    assert resp.status_code == 403


def test_refund_success(client):
    owner = _make_user(client, email="rok@example.com")
    created = client.post(
        "/orders",
        headers={"X-User-Id": str(owner["id"])},
        json={"items": [{"sku": "X", "quantity": 2, "unit_price": 5.00}]},
    ).json()
    resp = client.post(
        f"/orders/{created['id']}/refund",
        headers={"X-User-Id": str(owner["id"])},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["order_id"] == created["id"]
    assert body["amount"] == 1000
    assert body["refunded_at"]


def test_refund_second_call_rejected(client):
    owner = _make_user(client, email="ridem@example.com")
    created = client.post(
        "/orders",
        headers={"X-User-Id": str(owner["id"])},
        json={"items": [{"sku": "X", "quantity": 1, "unit_price": 1.00}]},
    ).json()
    headers = {"X-User-Id": str(owner["id"])}
    first = client.post(f"/orders/{created['id']}/refund", headers=headers)
    assert first.status_code == 200
    second = client.post(f"/orders/{created['id']}/refund", headers=headers)
    assert second.status_code == 400
    assert "already refunded" in second.json()["detail"]


def test_refund_window_expired(client, db_engine):
    from datetime import datetime, timedelta
    from sqlalchemy.orm import sessionmaker
    from api.models import Order

    owner = _make_user(client, email="rold@example.com")
    created = client.post(
        "/orders",
        headers={"X-User-Id": str(owner["id"])},
        json={"items": [{"sku": "X", "quantity": 1, "unit_price": 1.00}]},
    ).json()

    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    with Session() as s:
        order = s.get(Order, created["id"])
        order.created_at = datetime.utcnow() - timedelta(days=31)
        s.commit()

    resp = client.post(
        f"/orders/{created['id']}/refund",
        headers={"X-User-Id": str(owner["id"])},
    )
    assert resp.status_code == 400
    assert "window" in resp.json()["detail"]
```

## Critical files to modify

- `/Users/luisticas/bmad-demo/target/src/api/models.py` — add `refunded_at` column
- `/Users/luisticas/bmad-demo/target/src/api/routes/orders.py` — add import, constant, schema, handler
- `/Users/luisticas/bmad-demo/target/tests/test_orders.py` — append six tests

## Files reused (no changes)

- `src/api/deps.py` — `get_current_user`, `get_db` reused as-is
- `src/api/main.py` — orders router already registered, no router change needed
- `tests/conftest.py` — `client` and `db_engine` fixtures reused; the schema change is picked up automatically because the `db_engine` fixture calls `Base.metadata.create_all` each test

## Verification

1. `pytest tests/test_orders.py -v` — all 6 new tests plus existing tests pass
2. `pytest -x` — full suite passes (no regressions)
3. Optional manual curl after `uvicorn`:
   ```
   curl -X POST localhost:8000/users -H 'Content-Type: application/json' \
        -d '{"email":"a@b.com","name":"A"}'
   curl -X POST localhost:8000/orders -H 'X-User-Id: 1' \
        -H 'Content-Type: application/json' \
        -d '{"items":[{"sku":"X","quantity":1,"unit_price":9.99}]}'
   curl -X POST localhost:8000/orders/1/refund -H 'X-User-Id: 1'   # 200
   curl -X POST localhost:8000/orders/1/refund -H 'X-User-Id: 1'   # 400 already refunded
   ```
4. Confirm `/docs` shows the new endpoint with `RefundOut` schema.
