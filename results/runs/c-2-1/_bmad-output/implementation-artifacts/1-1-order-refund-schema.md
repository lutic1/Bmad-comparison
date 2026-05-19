# Story 1-1 — Order Model: Refund Fields

**Status:** review  
**Epic:** 1 — Order Refund Endpoint  
**Story:** 1 of 2  
**Depends on:** nothing (foundation story)  
**Blocks:** Story 1-2 (endpoint implementation)

---

## Brief

Add `refunded` (Boolean, non-nullable, default `False`) and `refunded_at` (DateTime, nullable) columns to the `Order` SQLAlchemy model, then extend the existing `OrderOut` Pydantic response model with the matching fields and update the two call sites (`create_order` and `get_order`) that construct it. This is a pure data-layer change — no new endpoint, no new business logic. It sets the foundation that Story 1-2 depends on. All five existing order tests must continue to pass after this change; the new fields will simply appear in existing responses with their defaults (`refunded: false`, `refunded_at: null`).

---

## Acceptance Criteria

| ID | Criterion |
|----|-----------|
| AC-S1-01 | `Order` model has `refunded: Mapped[bool]` with `Boolean` column, `default=False`, `nullable=False` |
| AC-S1-02 | `Order` model has `refunded_at: Mapped[datetime \| None]` with `DateTime` column, `nullable=True` |
| AC-S1-03 | `OrderOut` Pydantic model has `refunded: bool` and `refunded_at: str \| None` fields |
| AC-S1-04 | `create_order` response includes `refunded: false` and `refunded_at: null` for a new order |
| AC-S1-05 | `get_order` response includes `refunded: false` and `refunded_at: null` for an unrefunded order |
| AC-S1-06 | All existing `pytest` tests pass without modification |

---

## Files to Change

| File | Change type | What changes |
|------|-------------|--------------|
| `src/api/models.py` | UPDATE | Add `Boolean` to SQLAlchemy imports; add two columns to `Order` |
| `src/api/routes/orders.py` | UPDATE | Add two fields to `OrderOut`; pass them in both `OrderOut(...)` construction sites |

---

## Exact Changes

### `src/api/models.py`

Add `Boolean` to the existing SQLAlchemy import line:
```python
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
```

Append to `Order` class (after `created_at`):
```python
refunded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
refunded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

### `src/api/routes/orders.py`

Extend `OrderOut`:
```python
class OrderOut(BaseModel):
    id: int
    user_id: int
    total: int
    created_at: str
    items: list[OrderItemOut]
    refunded: bool           # new
    refunded_at: str | None  # new
```

In both `create_order` and `get_order`, add to the `OrderOut(...)` call:
```python
refunded=order.refunded,
refunded_at=order.refunded_at.isoformat() if order.refunded_at else None,
```

---

## Do NOT Change

- `src/api/main.py`
- `src/api/deps.py`
- `src/api/utils/dates.py`
- `tests/conftest.py`
- `tests/test_orders.py`
- `tests/test_users.py`
- `tests/test_dates.py`
- `pyproject.toml`

No new dependencies. No new endpoints. No migration needed (schema rebuilt from `Base.metadata`).

---

## Verification

```bash
pytest
```

All 11 existing tests green. No new tests in this story.
