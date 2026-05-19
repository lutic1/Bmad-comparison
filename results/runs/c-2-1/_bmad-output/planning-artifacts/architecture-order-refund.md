# Architecture — Order Refund Endpoint

**Status:** Draft  
**Author:** Winston (Architect)  
**Date:** 2026-05-18  
**PRD:** `prd-order-refund.md`

---

## 1. Overview

Four files change. No new files. No new dependencies. The change fits entirely within the existing FastAPI/SQLAlchemy/pytest patterns.

```
src/api/models.py          ← add 2 columns to Order
src/api/routes/orders.py   ← add RefundOut, update OrderOut, add route
tests/conftest.py          ← add db_session fixture
tests/test_orders.py       ← add 8 new test functions
```

---

## 2. Open Questions Resolved

| OQ | Decision |
|----|----------|
| OQ-1 | **Yes** — `OrderOut` grows `refunded: bool` and `refunded_at: str \| None`. AC-08 requires it. Additive, no breaking change. |
| OQ-2 | `timedelta(days=30)` comparison against UTC datetimes. Consistent with existing `datetime.utcnow()` usage throughout the codebase. |
| OQ-3 | Refunded orders remain retrievable via `GET /orders/{id}` — they are flagged, not deleted. |

---

## 3. Schema — `src/api/models.py`

Add `Boolean` to the SQLAlchemy import. Append two columns to `Order` using the existing `Mapped[...]` declarative style:

```python
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String

class Order(Base):
    # ... existing columns unchanged ...
    refunded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- `refunded` defaults to `False` at the SQLAlchemy level — existing and new orders are non-refunded on creation.
- `refunded_at` is nullable — `NULL` until a refund is processed.
- No migration needed (schema rebuilt from `Base.metadata` per project convention).

---

## 4. Routes — `src/api/routes/orders.py`

### 4.1 Import change

Add `timedelta` to the existing `datetime` import:

```python
from datetime import datetime, timedelta
```

### 4.2 `OrderOut` — add two fields

```python
class OrderOut(BaseModel):
    id: int
    user_id: int
    total: int
    created_at: str
    items: list[OrderItemOut]
    refunded: bool               # new
    refunded_at: str | None      # new
```

### 4.3 Update existing `OrderOut` construction sites

Both `create_order` and `get_order` manually construct `OrderOut(...)`. Each needs two new kwargs:

```python
refunded=order.refunded,
refunded_at=order.refunded_at.isoformat() if order.refunded_at else None,
```

No other logic in those handlers changes.

### 4.4 New Pydantic response model

```python
class RefundOut(BaseModel):
    order_id: int
    refunded: bool
    refunded_at: str    # ISO datetime string, e.g. "2026-05-18T14:30:00"
    total: int
```

`refunded_at` uses `.isoformat()` (includes time component) rather than the date-only `strftime` used by `created_at`. This is intentional — refund timestamps need sub-day precision.

### 4.5 New route handler

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
    if order.refunded:
        raise HTTPException(status_code=409, detail="order has already been refunded")
    if datetime.utcnow() - order.created_at > timedelta(days=30):
        raise HTTPException(status_code=422, detail="refund window of 30 days has expired")

    now = datetime.utcnow()
    order.refunded = True
    order.refunded_at = now
    db.commit()
    db.refresh(order)

    return RefundOut(
        order_id=order.id,
        refunded=True,
        refunded_at=now.isoformat(),
        total=order.total,
    )
```

**Guard ordering rationale:** 404 before 403 (can't check ownership if row is absent), 403 before 409/422 (ownership is a security gate, not a business rule), idempotency (409) before window (422) to give a clear signal on repeat calls.

---

## 5. Tests — `tests/conftest.py`

Add a `db_session` fixture so tests can reach the database directly (needed for the 30-day expiry scenario):

```python
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
```

This fixture depends on the existing `db_engine`, so it shares the same in-memory database as `client`. No changes to existing fixtures.

---

## 6. Tests — `tests/test_orders.py`

Eight new test functions, one AC per test. All follow the existing naming convention and use `_make_user` and `client`.

| Test name | AC | Method |
|-----------|-----|--------|
| `test_refund_requires_auth` | AC-01 | Call without header → 401 |
| `test_refund_unknown_user_401` | AC-02 | Call with non-existent user id → 401 |
| `test_refund_order_not_found` | AC-03 | Call with non-existent order_id → 404 |
| `test_refund_forbidden_for_other_user` | AC-04 | User B tries to refund User A's order → 403 |
| `test_refund_expired_window_422` | AC-05 | Backdate `created_at` 31 days via `db_session`, then call → 422 |
| `test_refund_success_200` | AC-06 | Happy path → 200, assert all response fields, assert DB state |
| `test_refund_already_refunded_409` | AC-07 | Call twice → second call is 409 |
| `test_refund_reflected_in_get_order` | AC-08 | Refund, then `GET /orders/{id}` → `refunded: true` in response |

**Expiry test pattern** (uses both `client` and `db_session` fixtures):

```python
def test_refund_expired_window_422(client, db_session):
    from datetime import timedelta
    from api.models import Order

    owner = _make_user(client, email="old@example.com")
    created = client.post(
        "/orders",
        headers={"X-User-Id": str(owner["id"])},
        json={"items": [{"sku": "X", "quantity": 1, "unit_price": 1.00}]},
    ).json()

    order = db_session.get(Order, created["id"])
    order.created_at = datetime.utcnow() - timedelta(days=31)
    db_session.commit()

    resp = client.post(
        f"/orders/{created['id']}/refund",
        headers={"X-User-Id": str(owner["id"])},
    )
    assert resp.status_code == 422
    assert "30 days" in resp.json()["detail"]
```

---

## 7. Trade-offs Considered

| Option | Decision | Reason |
|--------|----------|--------|
| Separate `Refund` table vs. columns on `Order` | **Columns on `Order`** | No multi-refund history needed (NG2, NG3); separate table adds join complexity for no gain at this scope |
| `RefundOut` vs. reuse `OrderOut` | **Separate `RefundOut`** | The refund response shape is distinct (no `items`, has `order_id`); coupling them would force nullability noise |
| `datetime.isoformat()` vs. matching existing `strftime` | **`isoformat()`** for `refunded_at` only | Existing `strftime("%Y-%d-%m")` is date-only (and has a day/month swap bug); refund timestamps need datetime precision. Not touching the existing format. |
| Import `timedelta` at module level vs. inside function | **Module level** | Consistent with how `datetime` is already imported |

---

## 8. What Does NOT Change

- `src/api/main.py` — router already included, lifespan unchanged
- `src/api/deps.py` — `get_current_user` and `get_db` are reused as-is
- `src/api/utils/dates.py` — not relevant to this feature
- `tests/test_users.py`, `tests/test_dates.py` — untouched
- `pyproject.toml` — no new dependencies

---

## 9. Implementation Checklist

For the developer picking this up:

- [ ] `models.py`: add `Boolean` import, add `refunded` + `refunded_at` columns to `Order`
- [ ] `routes/orders.py`: add `timedelta` import
- [ ] `routes/orders.py`: add `refunded` + `refunded_at` to `OrderOut`
- [ ] `routes/orders.py`: update `create_order` `OrderOut(...)` call
- [ ] `routes/orders.py`: update `get_order` `OrderOut(...)` call
- [ ] `routes/orders.py`: add `RefundOut` model
- [ ] `routes/orders.py`: add `refund_order` route handler
- [ ] `conftest.py`: add `db_session` fixture
- [ ] `test_orders.py`: add 8 new test functions
- [ ] Run `pytest` — all tests green including existing suite
