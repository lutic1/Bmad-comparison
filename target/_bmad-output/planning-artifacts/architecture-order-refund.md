# Architecture: Order Refund Endpoint

**Status:** Draft  
**Author:** Winston (Architect)  
**Date:** 2026-05-19  
**PRD:** `prd-order-refund.md`

---

## Summary

Three files change. No new files. No new dependencies. The feature is entirely additive — two new columns on `Order`, one new Pydantic model, one new route handler, and one new test file (or additional tests in the existing one).

---

## Open Question Resolutions

| OQ | Resolution | Rationale |
|---|---|---|
| OQ-1 | **Add `refunded` + `refunded_at` to `OrderOut`** | AC-9 requires GET to reflect state. Additive, non-breaking. |
| OQ-2 | **Align with existing: naive UTC, `datetime.utcnow()`** | Consistency > correctness for a small service; fixing naive datetimes is a separate task. |
| OQ-3 | **Rolling 720 h from `created_at`** (`timedelta(days=30)`) | Simpler than calendar-day math; "30 days from creation" maps naturally to a timedelta. |
| OQ-4 | **Error priority: 404 → 403 → 409 → 422** | Natural validation flow: existence before ownership, state before window. |

---

## File-by-File Changes

### 1. `src/api/models.py`

Add two columns to the `Order` model. No other model changes.

```python
# Add imports
from sqlalchemy import Boolean

# Inside class Order:
refunded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
refunded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

`datetime` is already imported in this file. `Boolean` needs to be added to the `sqlalchemy` import line.

**Why not a separate `Refund` table?** The PRD explicitly rules out partial refunds, audit history, and multiple refund states. A separate table would be premature. Two columns on `Order` satisfy every requirement.

---

### 2. `src/api/routes/orders.py`

Three additive changes:

#### 2a. Extend `OrderOut` (resolves OQ-1 / AC-9)

```python
class OrderOut(BaseModel):
    id: int
    user_id: int
    total: int
    created_at: str
    items: list[OrderItemOut]
    refunded: bool          # new
    refunded_at: str | None  # new
```

All existing callsites that construct `OrderOut` must pass the two new fields. Both default to `False` / `None` on the model, so existing orders are unaffected logically — but the Pydantic model is not constructed with `from_attributes`, it's built manually, so each `OrderOut(...)` call needs the two new kwargs.

**Existing `OrderOut` construction sites:**
- `create_order` → add `refunded=order.refunded, refunded_at=None`
- `get_order` → add `refunded=order.refunded, refunded_at=order.refunded_at.isoformat() if order.refunded_at else None`

#### 2b. New Pydantic response model

```python
class RefundOut(BaseModel):
    order_id: int
    refunded_at: str
    total_refunded: int
```

#### 2c. New route handler

```python
from datetime import timedelta

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

`datetime` and `timedelta` are stdlib — no new dependencies. `timedelta` needs to be added to the `from datetime import datetime` line.

**Route ordering note:** FastAPI matches routes top-to-bottom. `/{order_id}/refund` must be registered before any `/{order_id}/{sub}` wildcards. Currently there are none, so placement at the end of the file is fine.

---

### 3. `tests/test_orders.py` (or new `tests/test_refund.py`)

**Recommendation:** Add to `test_orders.py` to keep all order-related tests co-located, consistent with existing structure.

#### Test helper needed: time travel

The 30-day boundary tests (AC-7, AC-8) require manipulating `order.created_at`. The `client` fixture does not expose a raw db session, but `db_engine` is available via fixture inheritance.

Add a `db` fixture to `conftest.py`:

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

Tests that need time travel accept both `client` and `db` fixtures, create the order via HTTP, then directly update `created_at` via the SQLAlchemy session before issuing the refund request.

#### Test cases (maps to AC-1 through AC-9)

| Test name | AC |
|---|---|
| `test_refund_success` | AC-1 |
| `test_refund_requires_auth` | AC-2 |
| `test_refund_unknown_user` | AC-3 |
| `test_refund_order_not_found` | AC-4 |
| `test_refund_forbidden_other_user` | AC-5 |
| `test_refund_already_refunded` | AC-6 |
| `test_refund_expired_window` | AC-7 |
| `test_refund_boundary_exactly_30_days` | AC-8 |
| `test_refund_persists_state` | AC-9 |

---

## Sequence: Happy Path

```
Client
  → POST /orders/{id}/refund  [X-User-Id: 1]
  → get_current_user()         [401 if missing/unknown]
  → db.get(Order, id)          [404 if not found]
  → order.user_id == user.id   [403 if mismatch]
  → order.refunded == False    [409 if already refunded]
  → utcnow() - created_at ≤ 30d [422 if expired]
  → order.refunded = True
  → order.refunded_at = utcnow()
  → db.commit()
  → 201 RefundOut{order_id, refunded_at, total_refunded}
```

---

## What Does NOT Change

- `src/api/deps.py` — no changes, auth reused as-is
- `src/api/main.py` — no changes, orders router already registered
- `src/api/routes/users.py` — no changes
- `src/api/utils/` — no changes
- `pyproject.toml` — no new dependencies
- `tests/conftest.py` — one additive fixture (`db`) only

---

## Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Existing `OrderOut` callers break after adding required fields | Certain (known sites) | Explicitly update both construction sites in `create_order` and `get_order` |
| `datetime.utcnow()` deprecation warning in Python 3.12 | Low (test noise only) | Out of scope; align with existing pattern, track separately |
| SQLite `Boolean` stored as 0/1 — Pydantic may serialize as int | Low | SQLAlchemy `Boolean` coerces correctly; Pydantic v2 handles `bool` |

