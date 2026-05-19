# Add `POST /orders/{order_id}/refund`

## Context

The orders API currently supports creating and retrieving orders, but has no
way to refund one. We need an authenticated endpoint that lets the order's
owner refund it within 30 days of creation, marks the order as refunded
(idempotent — second call rejected), and returns the refund record.

There is no existing refund/payment code, and the `Order` model has no status
field today. Schema changes are fine: per `CLAUDE.md`, the operator wipes
`app.db` between runs and no migrations are needed.

## Approach

1. **New `Refund` SQLAlchemy model** in `src/api/models.py` with a unique FK
   to `orders.id` (enforces one refund per order at the DB level).
2. **New route** `POST /orders/{order_id}/refund` in `src/api/routes/orders.py`
   that validates ownership, the 30-day window, and not-already-refunded,
   then creates and returns the refund.
3. **Tests** appended to `tests/test_orders.py` covering each branch.

Full refund only — no request body. Refund amount = `order.total` (cents).
This matches the "mark the order as refunded" wording and avoids designing
partial-refund semantics that weren't asked for.

## Changes

### 1. `src/api/models.py` — add `Refund` model

```python
class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), nullable=False, unique=True
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # cents
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    order: Mapped["Order"] = relationship()
```

Notes:
- `unique=True` on `order_id` is the source of truth for "one refund per
  order"; the route does an explicit pre-check for a clean 400 error rather
  than letting the IntegrityError bubble.
- No back-populates relationship on `Order` — not needed for this endpoint
  and avoids touching the existing model.

### 2. `src/api/routes/orders.py` — add response model + route

Add `Refund` to the model import. Add a Pydantic response model alongside
the existing ones (same style — schemas live in the route file):

```python
class RefundOut(BaseModel):
    id: int
    order_id: int
    amount: int
    created_at: str
```

Add the route after `get_order` (before the helper functions at the bottom):

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
        raise HTTPException(
            status_code=400, detail="refund window has expired"
        )

    existing = (
        db.query(Refund).filter(Refund.order_id == order.id).one_or_none()
    )
    if existing is not None:
        raise HTTPException(status_code=400, detail="order already refunded")

    refund = Refund(order_id=order.id, amount=order.total)
    db.add(refund)
    db.commit()
    db.refresh(refund)

    return RefundOut(
        id=refund.id,
        order_id=refund.order_id,
        amount=refund.amount,
        created_at=refund.created_at.strftime("%Y-%d-%m"),
    )
```

Required imports to add at the top of the file:
- `from datetime import datetime, timedelta` (replaces existing `datetime` import)
- Add `Refund` to the `from api.models import ...` line

The `created_at` format matches the existing `%Y-%d-%m` pattern used by
`create_order`/`get_order` for consistency — not fixing that here per
"don't refactor unrelated code".

### 3. `tests/test_orders.py` — add refund tests

Reuse the existing `_make_user` helper and `client` fixture. Cases:

- `test_refund_requires_auth` — POST without `X-User-Id` → 401.
- `test_refund_not_found` — POST for a non-existent order id → 404.
- `test_refund_forbidden_for_other_user` — owner A creates order, user B
  tries to refund → 403.
- `test_refund_outside_30_day_window` — create order, then directly mutate
  `order.created_at` in the test DB to 31 days ago via a fresh session bound
  to the same engine, then POST → 400. (The DB session in the test can
  reach in via `TestingSessionLocal`; alternatively, monkeypatch
  `api.routes.orders.datetime` to advance "now" 31 days. Will use the
  monkeypatch approach — no coupling to test fixture internals.)
- `test_refund_success` — POST → 201, response has `id`, `order_id`,
  `amount` matching `order.total` in cents, and a `created_at` string.
- `test_refund_already_refunded` — POST twice → second call returns 400.

Monkeypatch pattern for the 30-day test:

```python
def test_refund_outside_30_day_window(client, monkeypatch):
    user = _make_user(client)
    headers = {"X-User-Id": str(user["id"])}
    order = client.post(
        "/orders",
        headers=headers,
        json={"items": [{"sku": "A", "quantity": 1, "unit_price": 9.99}]},
    ).json()

    from api.routes import orders as orders_module
    real_datetime = orders_module.datetime

    class FakeDatetime(real_datetime):
        @classmethod
        def utcnow(cls):
            return real_datetime.utcnow() + timedelta(days=31)

    monkeypatch.setattr(orders_module, "datetime", FakeDatetime)
    resp = client.post(f"/orders/{order['id']}/refund", headers=headers)
    assert resp.status_code == 400
```

## Critical files

- `src/api/models.py` — add `Refund` class.
- `src/api/routes/orders.py` — add route, response schema, imports.
- `tests/test_orders.py` — add ~6 tests.

## Verification

```bash
cd /Users/luisticas/bmad-demo/target
pytest tests/test_orders.py -v
```

All new tests should pass; existing tests should remain green. The
in-memory SQLite test fixture in `tests/conftest.py` calls
`Base.metadata.create_all`, so the new `refunds` table is created
automatically once the model is imported.
