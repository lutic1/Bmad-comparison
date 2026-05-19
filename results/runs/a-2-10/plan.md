# Add `POST /orders/{order_id}/refund`

## Context

The orders service has no refund flow today (verified — `refund` appears nowhere in the repo). We need an endpoint that lets an authenticated user refund their own order within 30 days of creation, marks the order as refunded so the operation can't repeat, and returns a refund record.

The design follows the existing patterns: small inline route, inline Pydantic schemas, naive-UTC timestamps, `X-User-Id` auth via `get_current_user`, and a single mutable column on `Order` rather than a new table (per CLAUDE.md: "Don't introduce abstractions for a single call site").

## Design decisions

- **No new `Refund` table.** Add a nullable `refunded_at: datetime | None` column to `Order`. Refunded iff `refunded_at is not None`; this doubles as state flag *and* timestamp. Matches the task hint "add a field if needed".
- **30-day window.** `datetime.utcnow() - order.created_at > timedelta(days=30)` → reject. Stays consistent with the existing naive-UTC convention on `Order.created_at` (models.py:32).
- **Refund amount.** Mirror the order total (cents). No partial refunds — out of scope.
- **Status codes.** Match existing route conventions:
  - 401 — missing/invalid `X-User-Id` (already produced by `get_current_user`)
  - 404 — order doesn't exist
  - 403 — order belongs to a different user (matches `test_get_order_forbidden_for_other_user`)
  - 400 — already refunded, or outside 30-day window
- **Date serialization.** Match the existing `_format_created_at` helper (`%Y-%d-%m`) for the response so the format is consistent with `OrderOut`.

## Files to modify

### 1. `src/api/models.py` — add column

In the `Order` class (after `created_at`, around line 32):

```python
refunded_at: Mapped[datetime | None] = mapped_column(
    DateTime, nullable=True, default=None
)
```

Schema is created from `Base.metadata` at startup (`src/api/main.py:10-13`); CLAUDE.md says the operator wipes `app.db` between runs — no migration needed.

### 2. `src/api/routes/orders.py` — add schema + handler

Add inline near the other Pydantic models (after `OrderOut`, ~line 41):

```python
class RefundOut(BaseModel):
    order_id: int
    user_id: int
    amount: int           # cents, equal to order.total
    refunded_at: str      # formatted with _format_created_at
```

Add a handler after `get_order` (~line 106). Reuse `get_db`, `get_current_user`, and `_format_created_at` already in the file:

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
    if datetime.utcnow() - order.created_at > timedelta(days=30):
        raise HTTPException(status_code=400, detail="refund window expired")

    order.refunded_at = datetime.utcnow()
    db.commit()
    db.refresh(order)

    return RefundOut(
        order_id=order.id,
        user_id=order.user_id,
        amount=order.total,
        refunded_at=_format_created_at(order.refunded_at),
    )
```

Imports to add at the top of `orders.py`: `timedelta` from `datetime` (already imports `datetime`), and `User` from `..models` if not already present (used only for the type hint — `get_current_user` already returns it).

### 3. `tests/conftest.py` — expose a session fixture

The 30-day test needs to backdate `created_at` directly in the DB. Add a minimal fixture (~5 lines) alongside the existing `client` fixture, bound to the same `db_engine`:

```python
@pytest.fixture()
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
```

Tests that use both `client` and `db_session` share the in-memory DB via `StaticPool` (already configured in `db_engine`).

### 4. `tests/test_orders.py` — add refund tests

Reuse the existing `_make_user` helper. Add at the bottom:

- `test_refund_requires_auth` — POST without `X-User-Id` → 401.
- `test_refund_unknown_order_returns_404` — POST `/orders/9999/refund` with valid user → 404.
- `test_refund_forbidden_for_other_user` — user A creates order, user B tries to refund → 403.
- `test_refund_marks_order_refunded` — happy path: create order, POST refund, assert 200, response has `order_id`, `user_id`, `amount` (equals order total in cents), `refunded_at` is a non-empty string.
- `test_refund_twice_rejected` — refund once succeeds, second refund → 400.
- `test_refund_outside_window_rejected` — uses `db_session` to set `order.created_at = datetime.utcnow() - timedelta(days=31)`, commit, then POST refund → 400.

## Verification

```bash
cd /Users/luisticas/bmad-demo/target
python -m pytest tests/test_orders.py -v
python -m pytest                            # full suite (should be all green)
```

Manual smoke check (optional):

```bash
uvicorn src.api.main:app --reload
# create user, create order, POST /orders/{id}/refund with X-User-Id header,
# verify second POST returns 400.
```

## Out of scope

- Partial refunds / refund amounts different from order total.
- Separate `Refund` audit table (one row per refund attempt).
- Refund reasons, admin override, or unrefund.
- Changing `_format_created_at`'s odd `%Y-%d-%m` format (CLAUDE.md: don't refactor unrelated code).
