# Data Model: Order Refund

**Feature**: `001-order-refund`
**Date**: 2026-05-19

## Modified Entities

### Order (existing — modified)

**File**: `src/api/models.py`

Two new columns added to the `orders` table:

| Column | SQLAlchemy type | Nullable | Default | Notes |
|--------|----------------|----------|---------|-------|
| `refunded` | `Boolean` | No | `False` | Set to `True` when a refund is accepted |
| `refunded_at` | `DateTime` | Yes | `NULL` | UTC timestamp recorded at refund time |

No columns are removed. No existing columns are changed.

SQLAlchemy declarative additions:

```python
refunded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
refunded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

**State transitions**:

```
not_refunded (refunded=False, refunded_at=NULL)
      │
      │  POST /orders/{id}/refund
      │  preconditions: within 30 days, requesting user is owner,
      │                 order not already refunded
      ▼
refunded (refunded=True, refunded_at=<utc timestamp>)
```

The `refunded` transition is **terminal** — no reverse transition is defined or in scope.

---

## Response Models (Pydantic v2)

### RefundOut

Returned by `POST /orders/{order_id}/refund` on success (HTTP 200).

| Field | Python type | Source |
|-------|-------------|--------|
| `order_id` | `int` | `order.id` |
| `refunded_at` | `str` | `order.refunded_at` formatted as ISO 8601 |
| `total` | `int` | `order.total` (integer cents) |

---

## Schema Migration Note

The `orders` table gains two new columns. Per project conventions there are no migrations; the operator must wipe `app.db` between service restarts after this change is deployed. The test suite uses an in-memory SQLite database recreated fresh per test — no operator action is required for tests.
