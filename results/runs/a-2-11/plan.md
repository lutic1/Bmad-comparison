# Plan: `POST /orders/{order_id}/refund`

## Context

The service has `POST /orders` and `GET /orders/{order_id}` but no way to refund.
We need an authenticated endpoint that marks an order as refunded, but only if
it belongs to the caller and was created within the last 30 days, then returns
a refund record describing what happened. The CLAUDE.md guardrails ("don't
introduce abstractions for a single call site", "stdlib first") and the
existing Order model (no status/state fields) push toward storing refund state
inline on `Order` rather than introducing a separate `Refund` table.

## Approach

1. **Schema change** — add a single nullable column `refunded_at: datetime | None`
   to `Order`. No migration needed (CLAUDE.md: operator wipes `app.db`).
2. **Endpoint** — add `POST /orders/{order_id}/refund` in `routes/orders.py`,
   reusing `get_current_user` and the same 404/403 pattern already in
   `get_order` (orders.py:85-106).
3. **Response shape** — return a `RefundOut` Pydantic model with the refund
   details (order_id, amount refunded in cents, refunded_at as string).
4. **Tests** — cover the golden path and the four failure modes.

## Files to modify

### `src/api/models.py`

Add to the `Order` class (after `created_at` at line ~33):

```python
refunded_at: Mapped[datetime | None] = mapped_column(
    DateTime, nullable=True, default=None
)
```

### `src/api/routes/orders.py`

Add a `RefundOut` response model near the other Pydantic models (after
`OrderOut`, ~line 41):

```python
class RefundOut(BaseModel):
    order_id: int
    amount: int
    refunded_at: str
```

Add the route handler (after `get_order`, ~line 106). Follow the same shape as
`get_order` for the 404/403 checks, then add the refund-specific validation:

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
    if now - order.created_at > timedelta(days=30):
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

Note: `datetime` is already imported in this file (orders.py); add
`timedelta` to that same import.

### `tests/test_orders.py`

Add tests using the existing `_make_user` helper and `client` fixture. One
behaviour per test (CLAUDE.md):

- `test_refund_requires_auth` — POST without `X-User-Id` → 401
- `test_refund_unknown_order_returns_404`
- `test_refund_other_users_order_returns_403` — create order as user A, refund
  as user B → 403
- `test_refund_marks_order_and_returns_record` — golden path: create order,
  refund it, assert 201, response contains `order_id`, `amount` (in cents),
  `refunded_at` string
- `test_refund_twice_returns_400` — second refund attempt → 400
- `test_refund_outside_30_days_returns_400` — manually set
  `created_at` to 31 days ago via the test DB session (use the
  `db_engine` fixture + a `sessionmaker` to mutate, or expose a helper
  fixture). Concretely: after creating the order, open a session against
  `db_engine`, fetch the order, set `created_at = datetime.utcnow() - timedelta(days=31)`,
  commit, then call the endpoint.

## Critical files

- `/Users/luisticas/bmad-demo/target/src/api/models.py` — add `refunded_at`
- `/Users/luisticas/bmad-demo/target/src/api/routes/orders.py` — add route + schema
- `/Users/luisticas/bmad-demo/target/tests/test_orders.py` — add tests

## Reused utilities/patterns

- `get_current_user` (deps.py:23) — auth
- `get_db` (deps.py:14) — DB session
- 404/403 pattern from `get_order` (orders.py:91-95)
- `_make_user` test helper (test_orders.py:1)
- `client` fixture (conftest.py:26) — already wires in-memory SQLite
- `dt.strftime("%Y-%d-%m")` — existing date-format pattern

## What we are NOT doing

- Not creating a separate `Refund` table (single-call-site abstraction).
- Not adding partial refunds, refund reasons, or amount overrides — task
  doesn't ask for them.
- Not adding logging/metrics (CLAUDE.md forbids unless asked).
- Not writing a migration — schema is rebuilt from `Base.metadata` at startup
  and the operator wipes `app.db`.

## Verification

1. `pytest tests/test_orders.py -v` — all new tests pass, existing ones still pass.
2. Manual smoke (optional):
   ```
   uvicorn src.api.main:app
   curl -X POST localhost:8000/users -H 'content-type: application/json' \
     -d '{"email":"a@b.c","name":"A"}'
   curl -X POST localhost:8000/orders -H 'X-User-Id: 1' \
     -H 'content-type: application/json' \
     -d '{"items":[{"sku":"X","quantity":1,"unit_price":9.99}]}'
   curl -X POST localhost:8000/orders/1/refund -H 'X-User-Id: 1'
   ```
   Expect 201 with refund record. Re-running the refund call returns 400.
