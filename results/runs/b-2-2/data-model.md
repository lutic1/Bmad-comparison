# Data Model: Order Refund

**Date**: 2026-05-19
**Feature**: [spec.md](spec.md)

---

## Modified Entity: Order

The existing `Order` SQLAlchemy model gains two new columns.

### New Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `refunded` | `bool` | No | `False` | Whether this order has been refunded |
| `refunded_at` | `datetime` | Yes | `None` | UTC timestamp of when the refund was processed |

### State Transitions

```
Order created
      │
      ▼
 refunded=False
 refunded_at=None
      │
      │  POST /orders/{id}/refund (within 30 days, first call)
      ▼
 refunded=True
 refunded_at=<utcnow>   ← terminal state; no further transitions allowed
```

### Validation Rules

- `refunded_at` MUST be set if and only if `refunded=True`.
- A refunded order MUST NOT transition back to `refunded=False`.
- The 30-day window is calculated from `created_at` to the request time using `datetime.utcnow() - created_at <= timedelta(days=30)`.

---

## New Response Model: RefundOut

Response-only Pydantic model — not persisted as its own table. The `Order` row is the source of truth.

| Field | Type | Source |
|-------|------|--------|
| `order_id` | `int` | `order.id` |
| `user_id` | `int` | `order.user_id` |
| `refunded_at` | `datetime` | `order.refunded_at` (set at refund time) |

---

## Unchanged Entities

`User`, `OrderItem` — no changes.
