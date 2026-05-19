# Plan: `POST /orders/{order_id}/refund`

## Context

The orders service has no refund flow yet. Customers need a way to refund an
order they placed, but only within a 30-day window, and the system must
guard against refunding the wrong user's order or double-refunding. This
plan adds a single endpoint plus the minimum schema needed to record the
refund.

Conventions followed (from `target/CLAUDE.md`):
- Stdlib first, no new dependencies.
- Schema created from `Base.metadata` at startup — no migration file.
- Auth via the existing `X-User-Id` header / `get_current_user` dependency.
- Tests required.

## Behavior summary

`POST /orders/{order_id}/refund`

| Condition                                              | Status | Detail                               |
| ------------------------------------------------------ | ------ | ------------------------------------ |
| Missing/unknown `X-User-Id`                            | 401    | (handled by `get_current_user`)      |
| Order does not exist                                   | 404    | `"order not found"`                  |
| Order belongs to a different user                      | 403    | `"forbidden"`                        |
| Order created more than 30 days ago                    | 400    | `"refund window expired"`            |
| Order already refunded                                 | 400    | `"order already refunded"`           |
| Success                                                | 201    | Refund record JSON                   |

A refund is for the order's full `total` (cents). The task does not ask for
partial refunds, so we do not add an `amount` parameter to the request.

## Files to modify

### 1. `src/api/models.py`

- Add `refunded_at: Mapped[datetime | None]` to `Order` (nullable; `None`
  means "not refunded"). This is the "mark the order as refunded" field.
- Add a `Refund` model:
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
  ```
  `unique=True` on `order_id` is a defense-in-depth guard for the
  "already refunded" case — the route still checks explicitly so we
  return a clean 400 rather than a 500.

### 2. `src/api/routes/orders.py`

- Import `Refund` from `api.models`.
- Add a `REFUND_WINDOW_DAYS = 30` constant near the top of the file (just
  below `_to_cents`).
- Add a `RefundOut` Pydantic response model:
  ```python
  class RefundOut(BaseModel):
      id: int
      order_id: int
      amount: int
      created_at: str
  ```
  `created_at` is a string formatted with the existing
  `_format_created_at` helper (line 126), matching how `OrderOut`
  serializes timestamps.
- Add the route handler (place after `get_order`, before the helper
  functions starting at line 109):
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
      if order.refunded_at is not None:
          raise HTTPException(status_code=400, detail="order already refunded")
      now = datetime.utcnow()
      if now - order.created_at > timedelta(days=REFUND_WINDOW_DAYS):
          raise HTTPException(status_code=400, detail="refund window expired")

      refund = Refund(order_id=order.id, amount=order.total, created_at=now)
      order.refunded_at = now
      db.add(refund)
      db.commit()
      db.refresh(refund)

      return RefundOut(
          id=refund.id,
          order_id=refund.order_id,
          amount=refund.amount,
          created_at=_format_created_at(refund.created_at),
      )
  ```
- Add `timedelta` to the existing `from datetime import datetime` import.

Existing helpers reused:
- `get_current_user` / `get_db` from `api.deps` (already imported).
- `_format_created_at` at `src/api/routes/orders.py:126`.

### 3. `tests/test_orders.py`

Append the following tests. They use the existing `_make_user` helper
already at the top of the file and the `client` fixture from
`tests/conftest.py`.

- `test_refund_requires_auth` — POST without `X-User-Id` → 401.
- `test_refund_order_not_found` — POST `/orders/9999/refund` as a real
  user → 404.
- `test_refund_forbidden_for_other_user` — owner creates order; another
  user tries to refund → 403.
- `test_refund_success` — owner refunds their own order → 201; response
  has `order_id`, `amount == order.total`, and an `id`.
- `test_refund_twice_rejected` — second refund of the same order → 400
  with `"already refunded"`.
- `test_refund_outside_window_rejected` — directly mutate
  `order.created_at` to `datetime.utcnow() - timedelta(days=31)` via a
  short-lived session bound to the same `db_engine` fixture, then POST
  the refund → 400 with `"refund window expired"`.

For the time-window test, I will add a small `db_session` helper inside
the test that opens a `Session(bind=...)` against the in-memory engine
used by the `client` fixture. The conftest already exposes `db_engine`
as a fixture, so the test signature becomes
`def test_refund_outside_window_rejected(client, db_engine):`. This
keeps the test deterministic without freezing time or adding a
dependency like `freezegun`.

## Verification

From `/Users/luisticas/bmad-demo/target`:

```
pytest tests/test_orders.py -v
```

Expect all existing tests plus the six new refund tests to pass.

Manual smoke (optional):

```
uvicorn api.main:app --reload
# Create a user, then an order, then:
curl -X POST http://localhost:8000/orders/1/refund -H "X-User-Id: 1"
```

Should return a 201 with `{id, order_id, amount, created_at}`.

## Out of scope

- Partial refunds (no `amount` parameter on the request).
- Refund reasons / notes.
- Restocking order items or reversing inventory.
- Listing refunds (`GET /refunds`, `GET /orders/{id}/refund`).
- Migration script — per CLAUDE.md, the operator wipes `app.db`.
