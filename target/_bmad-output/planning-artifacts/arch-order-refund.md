# Architecture Design: Order Refund Endpoint

**Status:** Draft  
**Author:** Winston (Architect)  
**Date:** 2026-05-19  
**PRD ref:** `prd-order-refund.md`

---

## 1. Scope

Three files change. No new files, no new dependencies, no new routers.

| File | Change type |
|------|-------------|
| `src/api/models.py` | Add 2 columns to `Order` |
| `src/api/routes/orders.py` | Add `RefundOut` schema + `POST /{order_id}/refund` handler; update `OrderOut` |
| `tests/test_refunds.py` | **New** — dedicated test module for all refund ACs |

`src/api/main.py`, `src/api/deps.py`, `tests/conftest.py` — **no changes.**

---

## 2. Data Model — `src/api/models.py`

Add two columns to the `Order` class, following the existing `Mapped[...]` declarative style:

```python
from sqlalchemy import Boolean  # add to existing import

class Order(Base):
    # ... existing columns unchanged ...
    refunded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
```

**Decisions:**
- `nullable=False, default=False` on `refunded` matches the PRD and avoids NULL-as-false ambiguity.
- `nullable=True` on `refunded_at` — NULL means not yet refunded; a timestamp means it was. Clean sentinel.
- No migration needed per `CLAUDE.md`; schema is rebuilt from `Base.metadata` at startup. Wipe `app.db` between deploys.

---

## 3. Routes — `src/api/routes/orders.py`

### 3.1 Updated `OrderOut`

Resolving PRD open question OQ-1: **yes, expose `refunded` and `refunded_at` on `OrderOut`**.  
Rationale: suppressing refund state from the GET response would be surprising and force callers to infer state from the refund endpoint alone. Cost is two fields; benefit is a consistent single source of truth.

```python
class OrderOut(BaseModel):
    id: int
    user_id: int
    total: int
    created_at: str
    items: list[OrderItemOut]
    refunded: bool
    refunded_at: str | None  # ISO-8601 or None
```

Both `create_order` and `get_order` handlers already construct `OrderOut` manually, so add the two fields there too:

```python
OrderOut(
    ...
    refunded=order.refunded,
    refunded_at=order.refunded_at.isoformat() if order.refunded_at else None,
)
```

### 3.2 New `RefundOut` schema

```python
class RefundOut(BaseModel):
    order_id: int
    refunded_at: str   # ISO-8601
    total: int         # cents
```

### 3.3 New route handler

```python
from datetime import timedelta

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
    if datetime.utcnow() - order.created_at > timedelta(days=30):
        raise HTTPException(status_code=422, detail="refund window expired")

    order.refunded = True
    order.refunded_at = datetime.utcnow()
    db.commit()
    db.refresh(order)

    return RefundOut(
        order_id=order.id,
        refunded_at=order.refunded_at.isoformat(),
        total=order.total,
    )
```

**Guard order matters:**
1. 404 — order existence (cheapest gate, no ownership leak)
2. 403 — ownership (don't reveal refund state of other users' orders)
3. 409 — already refunded (before the window check — an already-refunded order from 31 days ago should 409, not 422)
4. 422 — window expired

**OQ-2 resolution:** `409 Conflict` for duplicate refund, not idempotent `200`.  
Rationale: idempotency is appropriate for PUT/PATCH semantics. POST-to-refund is an action; a second invocation is unambiguously a client logic error and should be surfaced as such.

**OQ-3 resolution:** Calendar days (30 × 24h via `timedelta(days=30)`), consistent with PRD assumption and existing `datetime.utcnow()` usage.

**`datetime.utcnow()` note:** The existing model uses `datetime.utcnow` as default; match that for consistency. If the codebase migrates to timezone-aware datetimes later, this changes everywhere at once.

---

## 4. Tests — `tests/test_refunds.py` (new file)

### 4.1 Test DB access for time-boundary tests

The `conftest.py` `client` fixture exposes no raw DB session. Tests that need to backdate `created_at` (AC-6, AC-7) need one. Add a local `db` fixture in the test file that shares `db_engine`:

```python
from sqlalchemy.orm import sessionmaker as _sessionmaker

@pytest.fixture
def db(db_engine):
    Session = _sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
```

Since `db_engine` is function-scoped, `client` and `db` in the same test function share the same in-memory SQLite — mutations via `db` are visible to HTTP calls through `client`.

### 4.2 Test helpers (file-local)

```python
def _make_user(client, email="u@example.com", name="U"):
    r = client.post("/users", json={"email": email, "name": name})
    assert r.status_code == 201
    return r.json()

def _make_order(client, user_id, sku="SKU1", qty=1, price=10.00):
    r = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": [{"sku": sku, "quantity": qty, "unit_price": price}]},
    )
    assert r.status_code == 201
    return r.json()

def _backdate(db, order_id, days):
    from datetime import datetime, timedelta
    from api.models import Order
    order = db.get(Order, order_id)
    order.created_at = datetime.utcnow() - timedelta(days=days)
    db.commit()
```

### 4.3 Test coverage map

| AC | Test name | Fixtures |
|----|-----------|----------|
| AC-1 | `test_refund_requires_auth` | `client` |
| AC-2 | `test_refund_unknown_user` | `client` |
| AC-3 | `test_refund_order_not_found` | `client` |
| AC-4 | `test_refund_forbidden_for_other_user` | `client` |
| AC-5 | `test_refund_within_window_succeeds` | `client` |
| AC-6 | `test_refund_at_boundary_succeeds` | `client`, `db` |
| AC-7 | `test_refund_expired_window_rejected` | `client`, `db` |
| AC-8 | `test_refund_already_refunded_returns_409` | `client` |
| AC-9 | `test_refund_sets_refunded_flag_and_timestamp` | `client` |
| AC-10 | `test_refund_visible_on_get_order` | `client` |
| AC-11 | `test_refund_returns_201` | `client` |
| AC-12 | `test_refund_response_shape` | `client` |

AC-13 (dedicated file) and AC-14 (existing tests unbroken) are structural — verified by running the full suite.

---

## 5. Decisions Summary

| Question | Decision | Rationale |
|----------|----------|-----------|
| OQ-1: Expose refund state on `GET /orders/{id}`? | **Yes** — add `refunded` + `refunded_at` to `OrderOut` | Consistency; suppressing state forces callers to make a second request |
| OQ-2: `409` or idempotent `200` on duplicate refund? | **409 Conflict** | POST is an action verb; double-submission is a client bug, not a retry |
| OQ-3: Calendar days or business days? | **Calendar days** via `timedelta(days=30)` | Simplest correct interpretation; no business-day utility exists |
| OQ-4: Block refunded orders from future mutations? | Out of scope v1. The `refunded` flag is available for guards when needed | Premature to add guard logic for endpoints that don't exist |
| New file or extend `orders.py`? | **Extend `orders.py`** | One endpoint doesn't justify a new router + `main.py` change |
| Extract 30-day check to `utils/dates.py`? | **Inline** | Single call site; Rule of Three before abstraction |

---

## 6. What Doesn't Change

- `src/api/main.py` — no new router to register
- `src/api/deps.py` — auth/DB plumbing unchanged
- `tests/conftest.py` — `db_engine` and `client` fixtures unchanged
- `pyproject.toml` — no new dependencies
