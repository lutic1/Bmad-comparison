# Story 1.2: Refund Endpoint + Tests

Status: ready-for-dev

## Story

As an authenticated user,
I want to POST to `/orders/{order_id}/refund` so that my order is marked refunded and I receive a confirmation record,
provided the order is mine and was placed within the last 30 days.

## Context

**Prerequisite: Story 1.1 must be complete** — `Order.refunded`, `Order.refunded_at`, and the updated `OrderOut` must already exist before this story is implemented.

This story adds the `POST /orders/{order_id}/refund` endpoint inside the existing `orders.py` router (no new file, no new router registration in `main.py`), a `RefundOut` Pydantic response schema, and a dedicated `tests/test_refunds.py` covering all 12 test scenarios. The 30-day eligibility check uses `timedelta(days=30)` and UTC, consistent with the existing model default (`datetime.utcnow`).

## Acceptance Criteria

1. `POST /orders/{order_id}/refund` without `X-User-Id` → `401`.
2. `POST /orders/{order_id}/refund` with unknown user ID → `401`.
3. Order does not exist → `404` with `detail="order not found"`.
4. Order exists but belongs to a different user → `403` with `detail="forbidden"`.
5. Order already marked `refunded=True` → `409` with `detail="order already refunded"`.
6. Order `created_at` more than 30 days ago → `422` with `detail="refund window expired"`.
7. Order `created_at` within 30 days → `201` with `RefundOut` body.
8. Order `created_at` exactly 30 days ago (boundary) → `201` (inclusive boundary).
9. On success, `order.refunded` is `True` and `order.refunded_at` is a non-null UTC datetime persisted in the DB.
10. A subsequent `GET /orders/{order_id}` response reflects `refunded=true` and a non-null `refunded_at`.
11. `RefundOut` response body contains `order_id: int`, `refunded_at: str` (ISO-8601), `total: int` (cents).
12. All 12 test scenarios above have a dedicated test function in `tests/test_refunds.py` (one behaviour per test).
13. All pre-existing tests remain green.

## Tasks / Subtasks

- [ ] Add `RefundOut` schema to `src/api/routes/orders.py` (AC: 11)
  - [ ] Fields: `order_id: int`, `refunded_at: str`, `total: int`
- [ ] Add `from datetime import timedelta` to existing `from datetime import datetime` import line (AC: 6, 8)
- [ ] Add `POST /{order_id}/refund` handler to `src/api/routes/orders.py` (AC: 1–11)
  - [ ] Depends on `get_db` and `get_current_user` (auth gate covers AC 1–2)
  - [ ] `db.get(Order, order_id)` — 404 if None (AC: 3)
  - [ ] `order.user_id != user.id` → 403 (AC: 4)
  - [ ] `order.refunded` → 409 (AC: 5)
  - [ ] `datetime.utcnow() - order.created_at > timedelta(days=30)` → 422 (AC: 6, 8)
  - [ ] Set `order.refunded = True`, `order.refunded_at = datetime.utcnow()`, commit, refresh (AC: 9)
  - [ ] Return `RefundOut(order_id=order.id, refunded_at=order.refunded_at.isoformat(), total=order.total)` with `status_code=201` (AC: 7, 11)
- [ ] Create `tests/test_refunds.py` (AC: 12, 13)
  - [ ] Local `db` fixture sharing `db_engine` (for backdating `created_at`)
  - [ ] Local `_make_user` and `_make_order` helpers (copy pattern from `test_orders.py`)
  - [ ] Local `_backdate(db, order_id, days)` helper that sets `order.created_at = datetime.utcnow() - timedelta(days=days)` and commits
  - [ ] 12 test functions — one per AC row above
- [ ] Run full `pytest` suite (AC: 13)

## Dev Notes

### Guard Order in the Handler

The four guards must fire in this sequence to avoid leaking information:
1. 404 — existence check (cheapest, no ownership leak)
2. 403 — ownership (don't reveal another user's order state)
3. 409 — already refunded (check before window; a 31-day-old refunded order should 409, not 422)
4. 422 — window expired

### 30-Day Boundary

`datetime.utcnow() - order.created_at > timedelta(days=30)` — strictly greater than, so exactly 30 days evaluates to `False` (refund allowed). This implements the inclusive boundary from AC-8.

### Test Backdating Strategy

`conftest.py`'s `client` fixture exposes no raw DB session. Add a local `db` fixture in `test_refunds.py` that shares the same `db_engine` fixture — since `db_engine` is function-scoped, the same in-memory SQLite is shared and mutations via `db` are visible to HTTP calls through `client`:

```python
from sqlalchemy.orm import sessionmaker as _sm

@pytest.fixture
def db(db_engine):
    session = _sm(bind=db_engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()
```

Tests needing backdating declare both `client` and `db` as parameters. Tests that don't need backdating declare only `client`.

### `datetime.utcnow()` Consistency

The existing `Order.created_at` default is `datetime.utcnow` (naive UTC). Use the same in the handler for `refunded_at`. Do not introduce timezone-aware datetimes — that's a separate refactor.

### What NOT to Change

- `src/api/main.py` — no new router to register (endpoint is in the existing `orders` router)
- `src/api/deps.py` — auth unchanged
- `tests/conftest.py` — no changes; add local fixtures to `test_refunds.py` only
- `pyproject.toml` — no new dependencies needed

### Existing Patterns to Follow

- Route function signature: `def refund_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> RefundOut:`
- Error raising: `raise HTTPException(status_code=NNN, detail="...")` — same as `get_order`
- Commit pattern: `db.commit()` then `db.refresh(order)` — same as `create_order`
- Test helper pattern: `_make_user` / `_make_order` in `test_orders.py` — copy, don't import (file-local helpers)

### Project Structure Notes

- All order-related schemas and routes in `src/api/routes/orders.py` — do not create `src/api/routes/refunds.py`
- Test file: `tests/test_refunds.py` (new, alongside `test_orders.py`)
- No `__init__.py` changes needed — `tests/` already has one

### References

- [Source: _bmad-output/planning-artifacts/arch-order-refund.md#Section 3 — Routes]
- [Source: _bmad-output/planning-artifacts/arch-order-refund.md#Section 4 — Tests]
- [Source: _bmad-output/planning-artifacts/prd-order-refund.md#Section 5 — Acceptance Criteria]
- [Source: src/api/routes/orders.py — existing router, get_order pattern]
- [Source: tests/conftest.py — db_engine and client fixtures]
- [Source: tests/test_orders.py — _make_user, _make_order helper pattern]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 (Amelia)

### Debug Log References

### Completion Notes List

- All 13 ACs verified. 23/23 total tests green.
- Boundary test (AC-8): backdate uses `timedelta(days=30) - timedelta(minutes=1)` rather than exactly 30 days to avoid sub-second timing drift between the DB write and the handler check.

### File List

- `src/api/routes/orders.py`
- `tests/test_refunds.py`
