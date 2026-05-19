# Plan: `POST /orders/{order_id}/refund`

## Context

The orders service currently supports order creation and retrieval but has
no way to refund an order. We need an endpoint that lets the authenticated
owner of an order refund it within 30 days of creation, marks the order
as refunded so it can't be refunded again, and returns a refund record
describing what happened.

Following the project guardrails (no migrations — SQLite schema is recreated
from `Base.metadata` at startup; no abstractions for single call sites;
small route handlers with inline Pydantic models), we'll add a single
nullable `refunded_at` column to `Order` rather than a separate `Refund`
table. The "refund record" returned by the endpoint is a Pydantic response
shape, not a new persisted entity.

## Approach

### 1. Model change — `src/api/models.py`

Add one nullable column to `Order`:

```python
refunded_at: Mapped[datetime | None] = mapped_column(
    DateTime, nullable=True, default=None
)
```

`refunded_at is None` ⇒ not refunded. When set, the order is refunded
(timestamp doubles as the state flag, no separate boolean needed).

No migration — per `CLAUDE.md`, the operator wipes `app.db` between runs.

### 2. Route — `src/api/routes/orders.py`

Add a new handler in the existing router, alongside `create_order` /
`get_order`. Use the established patterns:

- `Depends(get_current_user)` for auth (401 handled by the dep).
- `db.get(Order, order_id)` → 404 if `None`.
- `order.user_id != user.id` → 403 `"forbidden"`.
- `order.refunded_at is not None` → 400 `"order already refunded"`.
- `datetime.utcnow() - order.created_at > timedelta(days=30)` → 400
  `"refund window expired"`. Both timestamps are naive UTC (see
  `User.created_at` / `Order.created_at` defaults), so direct subtraction
  is correct.
- Set `order.refunded_at = datetime.utcnow()`, `db.commit()`,
  `db.refresh(order)`.

Inline Pydantic response shape (matches the file's existing convention
of declaring models in the route file):

```python
class RefundOut(BaseModel):
    order_id: int
    amount: int          # cents, mirrors order.total
    refunded_at: str     # formatted with the existing _format_created_at
```

Reuse `_format_created_at` (already in `orders.py:126`) for the
`refunded_at` string — same `%Y-%d-%m` format the rest of the file uses,
keeping responses consistent even though the format is unusual.

Return `RefundOut(order_id=order.id, amount=order.total,
refunded_at=_format_created_at(order.refunded_at))`. Status 200 (no new
resource is created; the order is mutated).

### 3. Tests — `tests/test_orders.py`

Append tests using the existing `client` fixture and `_make_user` helper
(no new fixtures needed):

1. `test_refund_requires_auth` — POST without `X-User-Id` → 401.
2. `test_refund_order_not_found` — POST `/orders/9999/refund` → 404.
3. `test_refund_forbidden_for_other_user` — owner creates order, other
   user attempts refund → 403.
4. `test_refund_success_marks_order_and_returns_record` — refund
   succeeds, response contains `order_id`, `amount` (cents), and a
   `refunded_at` string.
5. `test_refund_twice_rejected` — second refund call → 400.
6. `test_refund_outside_window_rejected` — backdate `order.created_at`
   to 31 days ago via a direct DB session (use `deps.SessionLocal`
   override exposed through the test client's `dependency_overrides`,
   or import the test engine from `conftest`) → 400. Simplest path:
   reach into the app's overridden session factory via
   `app.dependency_overrides[deps.get_db]` to mutate the row, matching
   how `conftest.py` already wires things.

One behaviour per test, mirroring the existing file's style.

## Critical files

- `src/api/models.py` — add `refunded_at` column to `Order`.
- `src/api/routes/orders.py` — add `refund_order` handler + `RefundOut`
  model; reuse `_format_created_at`.
- `tests/test_orders.py` — add the six tests above.

## Verification

1. `cd /Users/luisticas/bmad-demo/target && pytest -q tests/test_orders.py`
   — all new tests pass, existing tests still pass.
2. Manual smoke (optional):
   - `uvicorn api.main:app --reload`
   - `POST /users` → grab id.
   - `POST /orders` with that `X-User-Id` → grab order id.
   - `POST /orders/{id}/refund` with same header → 200 + refund record.
   - Repeat → 400 "already refunded".
   - Other user → 403; unknown id → 404.
