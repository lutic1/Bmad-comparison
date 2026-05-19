# Data Model: Order Refund

**Feature**: `001-order-refund`
**Date**: 2026-05-19

---

## Schema Changes

### `orders` table — two new columns

| Column        | Type              | Nullable | Default | Notes                                |
|---------------|-------------------|----------|---------|--------------------------------------|
| `refunded`    | Boolean           | No       | False   | True once a refund has been recorded |
| `refunded_at` | DateTime          | Yes      | NULL    | UTC timestamp of refund; null until refunded |

**SQLAlchemy (declarative Mapped style)**:

```python
refunded: Mapped[bool] = mapped_column(default=False)
refunded_at: Mapped[datetime | None] = mapped_column(nullable=True)
```

No migration is required. The project uses schema-from-metadata at startup and
the operator wipes `app.db` between runs (see CLAUDE.md).

---

## Pydantic Response Model

### `RefundOut`

Returned by `POST /orders/{order_id}/refund` on success (HTTP 200).

| Field        | Type   | Description                                    |
|--------------|--------|------------------------------------------------|
| `order_id`   | int    | The refunded order's identifier                |
| `refunded`   | bool   | Always `true` in a successful refund response  |
| `refunded_at`| str    | Formatted refund timestamp (same format as `created_at` in OrderOut) |

```python
class RefundOut(BaseModel):
    order_id: int
    refunded: bool
    refunded_at: str
```

---

## State Transitions

```
Order.refunded = False  →  (POST /orders/{id}/refund, valid)  →  Order.refunded = True
Order.refunded = True   →  (POST /orders/{id}/refund)         →  422 already refunded
```

The transition is one-way and permanent. No un-refund operation exists.

---

## No New Entities

The `Refund Record` described in the spec is not a persisted entity. It is derived
from the updated `Order` row and returned in `RefundOut`. No new table or
relationship is introduced.
