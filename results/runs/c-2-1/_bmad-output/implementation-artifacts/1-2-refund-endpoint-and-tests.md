# Story 1-2 — Refund Endpoint + Tests

**Status:** review  
**Epic:** 1 — Order Refund Endpoint  
**Story:** 2 of 2  
**Depends on:** Story 1-1 (Order model must have `refunded` + `refunded_at` columns)

---

## Brief

Implement `POST /orders/{order_id}/refund` in `src/api/routes/orders.py` with the full guard chain (401 → 404 → 403 → 409 → 422 → 200), then add the supporting `db_session` fixture to `tests/conftest.py` and write eight new test functions in `tests/test_orders.py` — one per acceptance criterion. The endpoint reuses `get_current_user` for auth exactly as the existing `get_order` route does, uses `timedelta(days=30)` against UTC for the window check, and returns a dedicated `RefundOut` model (not `OrderOut`) because the refund response shape is distinct. The `db_session` fixture is required only for the 30-day expiry test, which must backdate `order.created_at` directly in the database to simulate a stale order. All pre-existing tests must remain green.

---

## Acceptance Criteria

| ID | Criterion |
|----|-----------|
| AC-01 | `POST /orders/{id}/refund` without `X-User-Id` header → `401` |
| AC-02 | `POST /orders/{id}/refund` with unknown user id → `401` |
| AC-03 | `POST /orders/9999/refund` (non-existent order) → `404` |
| AC-04 | User B requests refund on User A's order → `403` |
| AC-05 | Order created 31+ days ago, valid owner → `422` with `"30 days"` in detail |
| AC-06 | Valid owner, eligible order → `200` with `{order_id, refunded: true, refunded_at, total}`; DB row has `refunded=True` |
| AC-07 | Second call on already-refunded order (same owner) → `409` |
| AC-08 | After refund, `GET /orders/{id}` → `200` with `refunded: true` and non-null `refunded_at` |
| AC-09 | All existing tests still pass (`pytest` green) |

---

## Files to Change

| File | Change type | What changes |
|------|-------------|--------------|
| `src/api/routes/orders.py` | UPDATE | Add `timedelta` import; add `RefundOut`; add `refund_order` route |
| `tests/conftest.py` | UPDATE | Add `db_session` fixture |
| `tests/test_orders.py` | UPDATE | Add 8 new test functions |

---

## Exact Changes

### `src/api/routes/orders.py`

**Import change** — add `timedelta`:
```python
from datetime import datetime, timedelta
```

**New Pydantic model** (add after `OrderOut`):
```python
class RefundOut(BaseModel):
    order_id: int
    refunded: bool
    refunded_at: str  # ISO datetime, e.g. "2026-05-18T14:30:00"
    total: int
```

**New route** (add after `get_order`):
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

Guard order is intentional: 404 before 403 (row must exist to check ownership), 403 before 409/422 (security gate before business rules).

---

### `tests/conftest.py`

Add after the existing `client` fixture (add `sessionmaker` import if not already present at the top):
```python
@pytest.fixture
def db_session(db_engine):
    from sqlalchemy.orm import sessionmaker
    TestingSessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`db_session` depends on `db_engine` so it shares the exact same in-memory SQLite instance as `client`. No existing fixtures change.

---

### `tests/test_orders.py`

Add these 8 functions at the bottom of the file. Reuse the existing `_make_user` helper and `client` fixture throughout. Import `datetime` and `timedelta` at the top of the file if not already present.

```python
# ── Refund endpoint tests ──────────────────────────────────────────────────


def _make_order(client, user_id, sku="X", qty=1, price=1.00):
    resp = client.post(
        "/orders",
        headers={"X-User-Id": str(user_id)},
        json={"items": [{"sku": sku, "quantity": qty, "unit_price": price}]},
    )
    assert resp.status_code == 201
    return resp.json()


def test_refund_requires_auth(client):
    user = _make_user(client, email="auth1@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(f"/orders/{order['id']}/refund")
    assert resp.status_code == 401


def test_refund_unknown_user_401(client):
    user = _make_user(client, email="auth2@example.com")
    order = _make_order(client, user["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": "99999"},
    )
    assert resp.status_code == 401


def test_refund_order_not_found(client):
    user = _make_user(client, email="notfound@example.com")
    resp = client.post(
        "/orders/9999/refund",
        headers={"X-User-Id": str(user["id"])},
    )
    assert resp.status_code == 404


def test_refund_forbidden_for_other_user(client):
    owner = _make_user(client, email="rfowner@example.com")
    other = _make_user(client, email="rfother@example.com")
    order = _make_order(client, owner["id"])
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(other["id"])},
    )
    assert resp.status_code == 403


def test_refund_expired_window_422(client, db_session):
    from datetime import timedelta
    from api.models import Order

    owner = _make_user(client, email="expired@example.com")
    order = _make_order(client, owner["id"])

    row = db_session.get(Order, order["id"])
    row.created_at = datetime.utcnow() - timedelta(days=31)
    db_session.commit()

    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(owner["id"])},
    )
    assert resp.status_code == 422
    assert "30 days" in resp.json()["detail"]


def test_refund_success_200(client):
    owner = _make_user(client, email="success@example.com")
    order = _make_order(client, owner["id"], price=9.99)

    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(owner["id"])},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["order_id"] == order["id"]
    assert body["refunded"] is True
    assert body["refunded_at"] is not None
    assert body["total"] == 999


def test_refund_already_refunded_409(client):
    owner = _make_user(client, email="double@example.com")
    order = _make_order(client, owner["id"])

    client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(owner["id"])},
    )
    resp = client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(owner["id"])},
    )
    assert resp.status_code == 409


def test_refund_reflected_in_get_order(client):
    owner = _make_user(client, email="reflect@example.com")
    order = _make_order(client, owner["id"])

    client.post(
        f"/orders/{order['id']}/refund",
        headers={"X-User-Id": str(owner["id"])},
    )
    resp = client.get(
        f"/orders/{order['id']}",
        headers={"X-User-Id": str(owner["id"])},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["refunded"] is True
    assert body["refunded_at"] is not None
```

**Note:** `test_refund_expired_window_422` needs `from datetime import datetime` at the top of `test_orders.py` — add it if not already present.

---

## Do NOT Change

- `src/api/main.py` — router is already included
- `src/api/deps.py` — `get_current_user` and `get_db` reused as-is
- `src/api/models.py` — touched by Story 1-1, not this story
- `tests/test_users.py`, `tests/test_dates.py`
- `pyproject.toml`

---

## Verification

```bash
pytest
```

19 tests total (11 pre-existing + 8 new), all green.
