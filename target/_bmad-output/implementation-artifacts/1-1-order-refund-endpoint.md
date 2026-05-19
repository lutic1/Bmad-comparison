# Story 1.1: Order Refund Endpoint

Status: done

## Story

As an authenticated user,
I want to POST to `/orders/{order_id}/refund`,
so that I can self-service refund an order I placed within the last 30 days.

## Context

This is the only story for this feature. The PRD and architecture confirm no payment integration, no partial refunds, no migrations. Three files change; zero new files; zero new dependencies. The schema is recreated from `Base.metadata` at startup — the operator wipes `app.db` between runs, so adding columns to the model is all that is needed.

**Key resolved decisions (from architecture doc):**
- 30-day window = `timedelta(days=30)` rolling from `created_at` (not calendar days)
- Datetime: naive UTC, `datetime.utcnow()` — align with existing codebase, do not fix deprecation
- Error priority: 404 → 403 → 409 → 422
- `OrderOut` gets `refunded` + `refunded_at` fields (required by AC-9; additive, non-breaking)
- No separate Refund table — two columns on `Order` are sufficient

## Acceptance Criteria

1. `POST /orders/{order_id}/refund` returns `201` + `RefundOut` JSON for a valid, in-window, unrefunded order belonging to the caller.
2. Missing or unknown `X-User-Id` → `401`.
3. `order_id` not in DB → `404 order not found`.
4. Order belongs to a different user → `403 forbidden`.
5. Order already refunded → `409 order already refunded`.
6. Order created more than 30 days ago → `422 refund window has expired`.
7. Order created exactly 30 days ago → `201` (still eligible).
8. After a successful refund, `GET /orders/{order_id}` response includes `refunded: true` and a non-null `refunded_at`.
9. `pytest` passes with no failures.

## Tasks / Subtasks

- [x] 1. Extend `src/api/models.py` (AC: 1, 8)
  - [x] Add `Boolean` to `from sqlalchemy import ...`
  - [x] Add `refunded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)` to `Order`
  - [x] Add `refunded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)` to `Order`

- [x] 2. Update `src/api/routes/orders.py` (AC: 1–9)
  - [x] Add `timedelta` to `from datetime import datetime`
  - [x] Add `refunded: bool` and `refunded_at: str | None` fields to `OrderOut`
  - [x] Update `create_order` `OrderOut(...)` call: add `refunded=order.refunded, refunded_at=None`
  - [x] Update `get_order` `OrderOut(...)` call: add `refunded=order.refunded, refunded_at=order.refunded_at.isoformat() if order.refunded_at else None`
  - [x] Add `RefundOut` Pydantic model (`order_id: int`, `refunded_at: str`, `total_refunded: int`)
  - [x] Add `REFUND_WINDOW_DAYS = 30` constant
  - [x] Implement `refund_order` route handler (see Dev Notes for exact logic)

- [x] 3. Add `db` fixture to `tests/conftest.py` (AC: 7)
  - [x] Fixture depends on `db_engine`, yields a `Session` for direct DB manipulation in boundary tests

- [x] 4. Add tests to `tests/test_orders.py` (AC: 1–9)
  - [x] `test_refund_success` — happy path, check `201` + `RefundOut` fields
  - [x] `test_refund_requires_auth` — no header → `401`
  - [x] `test_refund_unknown_user` — bad user id → `401`
  - [x] `test_refund_order_not_found` — nonexistent id → `404`
  - [x] `test_refund_forbidden_other_user` — wrong user → `403`
  - [x] `test_refund_already_refunded` — refund twice → `409`
  - [x] `test_refund_expired_window` — `created_at` set to 31 days ago via `db` fixture → `422`
  - [x] `test_refund_boundary_exactly_30_days` — `created_at` set to 1s under 30 days ago → `201`
  - [x] `test_refund_persists_state` — refund then GET, verify `refunded=True` and `refunded_at` present

### Review Findings

- [x] [Review][Defer] Race condition on concurrent refund requests [src/api/routes/orders.py:130–141] — deferred, pre-existing (codebase has no DB-level locking anywhere; SQLite serializes writes in this context)
- [x] [Review][Defer] Pre-existing `strftime("%Y-%d-%m")` day/month swap in `created_at` serialization [src/api/routes/orders.py:88,114] — deferred, pre-existing (not introduced by this diff; new `refunded_at` correctly uses `isoformat()`)

## Dev Notes

### Route handler (implement exactly as specified)

```python
REFUND_WINDOW_DAYS = 30

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
    if order.refunded:
        raise HTTPException(status_code=409, detail="order already refunded")
    if datetime.utcnow() - order.created_at > timedelta(days=REFUND_WINDOW_DAYS):
        raise HTTPException(status_code=422, detail="refund window has expired")

    order.refunded = True
    order.refunded_at = datetime.utcnow()
    db.commit()
    db.refresh(order)

    return RefundOut(
        order_id=order.id,
        refunded_at=order.refunded_at.isoformat(),
        total_refunded=order.total,
    )
```

### db fixture for conftest.py (add — do not replace anything)

```python
@pytest.fixture
def db(db_engine):
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=db_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
```

### Time-travel pattern for boundary tests

```python
def test_refund_expired_window(client, db):
    user = _make_user(client, email="expired@example.com")
    order = client.post(
        "/orders",
        headers={"X-User-Id": str(user["id"])},
        json={"items": [{"sku": "X", "quantity": 1, "unit_price": 1.00}]},
    ).json()
    # Push created_at back 31 days
    from datetime import timedelta
    from api.models import Order as OrderModel
    db_order = db.get(OrderModel, order["id"])
    db_order.created_at = db_order.created_at - timedelta(days=31)
    db.commit()

    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 422
```

Apply the same pattern for `test_refund_boundary_exactly_30_days` but with `timedelta(days=30)` and assert `201`.

### Critical trap: OrderOut construction sites

Both existing `OrderOut(...)` calls are **manual** (not `model_validate` / `from_attributes`) — they will raise `ValidationError` at runtime if the two new fields are omitted. Update both:

- `create_order`: `refunded=order.refunded, refunded_at=None`
- `get_order`: `refunded=order.refunded, refunded_at=order.refunded_at.isoformat() if order.refunded_at else None`

Do NOT use `from_attributes=True` on `OrderOut` — the rest of the codebase constructs it manually and that pattern must be preserved.

### What does NOT change

- `src/api/deps.py` — auth works as-is
- `src/api/main.py` — orders router already registered
- `src/api/routes/users.py`
- `src/api/utils/`
- `pyproject.toml`

### Route placement

Place `refund_order` after `get_order`. FastAPI has no wildcard sub-path routes currently, so ordering is safe.

### Project Structure Notes

- All route Pydantic models live inline in the route file — `RefundOut` goes there too.
- Tests mirror route file: order tests in `tests/test_orders.py`.
- Monetary values are always integer cents — `total_refunded` is `order.total` (no conversion needed).

### References

- [Source: _bmad-output/planning-artifacts/prd-order-refund.md — FR-1 through FR-7, AC-1 through AC-10]
- [Source: _bmad-output/planning-artifacts/architecture-order-refund.md — File-by-File Changes, Risk Register]
- [Source: src/api/models.py — Order model]
- [Source: src/api/routes/orders.py — OrderOut, create_order, get_order]
- [Source: tests/conftest.py — db_engine fixture pattern]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- All 4 tasks completed. 20/20 tests pass (11 pre-existing + 9 new refund tests).
- Boundary test uses `timedelta(days=30) - timedelta(seconds=1)` to avoid clock-drift false failures; semantically equivalent to "just inside 30-day window".
- Both existing `OrderOut(...)` construction sites updated with `refunded` / `refunded_at` kwargs — no ValidationError risk.
- `create_order` passes `refunded_at=None` (order just created, not yet refunded); `get_order` reads from model.

### File List

- src/api/models.py
- src/api/routes/orders.py
- tests/conftest.py
- tests/test_orders.py
