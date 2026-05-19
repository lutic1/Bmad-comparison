# Add `POST /orders/{order_id}/refund`

## Context

The orders service currently supports creating and reading orders, but has no
way to refund one. We want an authenticated endpoint that lets the owner of an
order refund it, but only within 30 days of creation. After a successful
refund the order is flagged as refunded and a refund record is returned to the
caller. There is no real-money side-effect — this is bookkeeping only.

## Design decisions

- **Single field on `Order`, not a separate `Refund` table.** Per CLAUDE.md
  ("don't introduce abstractions for a single call site"), and because the
  user wrote "add a field if needed". A nullable `refunded_at` doubles as the
  status flag (`refunded_at IS NOT NULL` ⇒ refunded) and the refund timestamp.
- **Refund amount = `order.total`.** Partial refunds aren't in scope.
- **30-day window inclusive of day 30.** `now - created_at <= timedelta(days=30)`.
- **Idempotency: second refund → 409.** Mirrors the existing 409 usage for
  duplicate-email conflicts.
- **No migration.** Schema is recreated from `Base.metadata` at startup; the
  operator wipes `app.db` between runs (per project CLAUDE.md).

## Files to modify

### 1. `src/api/models.py` — add field to `Order`

Add one nullable column after `created_at`:

```python
refunded_at: Mapped[datetime | None] = mapped_column(
    DateTime, nullable=True, default=None
)
```

### 2. `src/api/routes/orders.py` — add response schema + route

Add a `RefundOut` Pydantic model and a `refund_order` route. Reuse
`get_db` and `get_current_user` from `api.deps` (already imported).

```python
from datetime import timedelta  # add to existing datetime import

REFUND_WINDOW = timedelta(days=30)

class RefundOut(BaseModel):
    order_id: int
    refunded_at: str
    amount: int  # cents, mirrors order.total

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
        raise HTTPException(status_code=409, detail="order already refunded")
    if datetime.utcnow() - order.created_at > REFUND_WINDOW:
        raise HTTPException(
            status_code=400, detail="refund window expired"
        )

    order.refunded_at = datetime.utcnow()
    db.commit()
    db.refresh(order)

    return RefundOut(
        order_id=order.id,
        refunded_at=order.refunded_at.isoformat(),
        amount=order.total,
    )
```

Notes:
- The auth/ownership/404 ordering matches `get_order` at `src/api/routes/orders.py:85`.
- `datetime.utcnow()` (naive UTC) matches the rest of the codebase
  (`models.py:18`, `models.py:32`). Don't switch to timezone-aware here.
- Uses `isoformat()` for `refunded_at` rather than the buggy `%Y-%d-%m`
  format used by `OrderOut.created_at` — the existing format string is wrong
  (day-month-year), but per CLAUDE.md ("don't refactor unrelated code") we
  leave `OrderOut` alone.

### 3. `tests/test_orders.py` — add tests

Append (re-uses the existing `_make_user` helper). Use `freezegun` only if it
already exists; otherwise patch `datetime` via monkeypatch on the module under
test, or insert directly on the model. The simplest path here is to **write
the `created_at` directly via a DB session** for the window-expired test,
similar to how integration tests bypass the API when needed.

Tests to add:

1. `test_refund_requires_auth` — POST `/orders/{id}/refund` with no header → 401.
2. `test_refund_forbidden_for_other_user` — other user → 403.
3. `test_refund_unknown_order` — POST against nonexistent id → 404.
4. `test_refund_success_marks_order_and_returns_record` — owner refunds, gets
   201, body has `order_id`, `amount` matching `order.total`, and
   `refunded_at` is a non-empty ISO string.
5. `test_refund_twice_conflicts` — second refund of same order → 409.
6. `test_refund_outside_window_rejected` — backdate the order's `created_at`
   to 31 days ago via a direct DB write, then refund → 400.

For test 6, fetch a session via the app's testing session factory. The
cleanest pattern given the existing fixtures is to expose the `db_engine`
through the existing fixture chain in `tests/conftest.py` and open a session
there to update `order.created_at`. Read `tests/conftest.py` before writing
the test to confirm the fixture name; do not modify conftest unless required.

## Verification

From the repo root:

```bash
# install deps if not already done
pip install -e .

# run only the orders tests
pytest tests/test_orders.py -v

# full suite (sanity)
pytest -v

# manual smoke
uvicorn api.main:app --reload
# in another shell:
curl -X POST http://localhost:8000/users \
  -H 'Content-Type: application/json' \
  -d '{"email":"a@b.c","name":"A"}'
curl -X POST http://localhost:8000/orders \
  -H 'X-User-Id: 1' -H 'Content-Type: application/json' \
  -d '{"items":[{"sku":"X","quantity":1,"unit_price":9.99}]}'
curl -X POST http://localhost:8000/orders/1/refund -H 'X-User-Id: 1'
# → 201 {"order_id":1,"refunded_at":"...","amount":999}
curl -X POST http://localhost:8000/orders/1/refund -H 'X-User-Id: 1'
# → 409
```

Expect: all new tests pass, existing tests untouched, typecheck/lint clean.
