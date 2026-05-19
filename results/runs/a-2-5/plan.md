# Add `POST /orders/{order_id}/refund`

## Context

The orders service currently supports creating and reading orders but has no
way to refund one. We need an endpoint that lets the order's owner refund
within a 30‑day window, persists the refunded state on the order, and returns
a refund record. No existing refund code is present.

The change must follow the conventions in `target/CLAUDE.md`: small route
functions in `src/api/routes/orders.py`, `X-User-Id`-based auth via
`api.deps.get_current_user`, no new dependencies, no migration (schema is
recreated from `Base.metadata` and `app.db` is wiped between runs), and
tests live in `tests/test_orders.py` using the existing `client` fixture.

## Design decisions

- **No separate `Refund` table.** Add a nullable `refunded_at` column to
  `Order`. There's no requirement for refund history, partials, or audit, so
  a separate table would be an abstraction for a single call site.
- **Refund window check** uses naive UTC: `datetime.utcnow() - order.created_at > timedelta(days=30)`.
  Matches the naive `datetime.utcnow` default on `Order.created_at`.
- **Double refund** returns `400 "order already refunded"`, consistent with
  other business-rule rejections in this file (e.g. empty items at
  `src/api/routes/orders.py:51`).
- **Response shape** `RefundOut`: `order_id: int`, `amount: int` (cents,
  equal to `order.total`), `refunded_at: str` formatted with
  `strftime("%Y-%d-%m")` to match the existing `OrderOut.created_at`
  formatting at `src/api/routes/orders.py:77,101`.
- **Status code** `201` — we're creating a refund record, mirroring
  `POST /orders`.
- **Check order**: 404 → 403 → already-refunded → window-expired. Matches the
  404-then-403 pattern in `get_order` at `src/api/routes/orders.py:91-95`.

## File changes

### `src/api/models.py` — add `refunded_at` to `Order`

Add one line to the `Order` model (after `created_at`):

```python
refunded_at: Mapped[datetime | None] = mapped_column(
    DateTime, nullable=True, default=None
)
```

No migration needed (per `target/CLAUDE.md`).

### `src/api/routes/orders.py` — add route and response model

1. Extend the existing datetime import:
   ```python
   from datetime import datetime, timedelta
   ```
2. Add `RefundOut` next to `OrderOut` (~line 42):
   ```python
   class RefundOut(BaseModel):
       order_id: int
       amount: int
       refunded_at: str
   ```
3. Add the route after `get_order` (after line 106), before the existing
   helpers:
   ```python
   REFUND_WINDOW = timedelta(days=30)


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
       if order.refunded_at is not None:
           raise HTTPException(status_code=400, detail="order already refunded")

       now = datetime.utcnow()
       if now - order.created_at > REFUND_WINDOW:
           raise HTTPException(status_code=400, detail="refund window expired")

       order.refunded_at = now
       db.commit()
       db.refresh(order)

       return RefundOut(
           order_id=order.id,
           amount=order.total,
           refunded_at=order.refunded_at.strftime("%Y-%d-%m"),
       )
   ```

### `tests/test_orders.py` — add refund tests

Add imports at the top of the file:
```python
from datetime import datetime, timedelta

from sqlalchemy.orm import sessionmaker

from api.models import Order
```

Add a small helper next to `_make_user`:
```python
def _make_order(client, user_id, sku="X", quantity=1, unit_price=10.00):
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": [{"sku": sku, "quantity": quantity, "unit_price": unit_price}]},
    )
    assert resp.status_code == 201
    return resp.json()
```

Add six tests covering:

- `test_refund_requires_auth` — no `X-User-Id` header → `401`.
- `test_refund_order_not_found` — unknown order id → `404`.
- `test_refund_forbidden_for_other_user` — order owned by user A, called by
  user B → `403` (mirrors `test_get_order_forbidden_for_other_user`).
- `test_refund_happy_path(client, db_engine)` — refund the owner's order,
  assert `201`, response body (`order_id`, `amount` in cents, `refunded_at`
  present), then open a `sessionmaker(bind=db_engine)` session to assert
  `order.refunded_at is not None` was persisted.
- `test_refund_outside_window_rejected(client, db_engine)` — create an order,
  backdate `created_at` to 31 days ago via a direct DB session bound to
  `db_engine`, then call the refund endpoint → `400` with detail `"refund
  window expired"`. Backdating beats monkey-patching `datetime.utcnow` —
  cleaner, no new dependency, doesn't depend on the route's clock call.
- `test_refund_already_refunded` — refund once (201), refund again (400 with
  detail `"order already refunded"`).

`db_engine` and `client` share the same function-scoped fixture instance
within a test (`tests/conftest.py:13-42`), so a `sessionmaker(bind=db_engine)`
in the test sees the same in-memory SQLite as the API.

## Critical files

- `/Users/luisticas/bmad-demo/target/src/api/models.py`
- `/Users/luisticas/bmad-demo/target/src/api/routes/orders.py`
- `/Users/luisticas/bmad-demo/target/tests/test_orders.py`
- `/Users/luisticas/bmad-demo/target/tests/conftest.py` (read-only reference)
- `/Users/luisticas/bmad-demo/target/src/api/deps.py` (read-only reference)

## Verification

From `/Users/luisticas/bmad-demo/target`:

- `pytest -k refund -v` — all six new tests pass.
- `pytest` — full suite still passes; existing tests don't touch
  `refunded_at`, and the new column is nullable with a default.
