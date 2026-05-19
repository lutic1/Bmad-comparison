# Phase 1 Data Model: Order Refund

## Changes to existing entities

### `Order` (src/api/models.py)

Add one column:

| Field         | Type                       | Nullable | Default | Notes                                      |
|---------------|----------------------------|----------|---------|--------------------------------------------|
| `refunded_at` | `Mapped[datetime \| None]` | yes      | `None`  | Set to the refund's `created_at` on refund |

Add a reverse relationship:

```python
refund: Mapped["Refund | None"] = relationship(
    back_populates="order", uselist=False
)
```

All other `Order` fields unchanged.

## New entities

### `Refund` (src/api/models.py)

| Field        | Type                       | Nullable | Default            | Notes                                    |
|--------------|----------------------------|----------|--------------------|------------------------------------------|
| `id`         | `Mapped[int]`              | no       | autoincrement      | Primary key                              |
| `order_id`   | `Mapped[int]`              | no       | —                  | FK → `orders.id`                         |
| `amount`     | `Mapped[int]`              | no       | —                  | Cents — copied from `Order.total`        |
| `created_at` | `Mapped[datetime]`         | no       | `datetime.utcnow`  | UTC, naive (matches project convention)  |

Relationship: `order: Mapped[Order] = relationship(back_populates="refund")`

Table: `__tablename__ = "refunds"`

Uniqueness: enforced at the application layer via the
`Order.refunded_at` check inside the refund transaction (see
research.md, Decision 8). No DB-level `UNIQUE(order_id)` constraint
added in v1.

## State transitions

`Order.refunded_at`:

```text
None ── POST /orders/{id}/refund (success) ──▶ <utc timestamp>
                                                     │
                                                     ▼
                                              (terminal — cannot
                                              transition back)
```

A refund row exists if and only if `Order.refunded_at` is non-null.

## Validation rules (enforced in the route handler)

1. `get_current_user` must succeed (else 401, raised by the dependency).
2. `db.get(Order, order_id)` must return a row whose `user_id` matches
   the current user — otherwise return 404 with detail
   `"order not found"`. Both "missing" and "not yours" share this
   response per the spec.
3. `order.refunded_at is None` — otherwise return 409 with detail
   `"order already refunded"`.
4. `datetime.utcnow() - order.created_at <= timedelta(days=30)` —
   otherwise return 422 with detail `"refund window expired"`.

On success, in a single transaction:

1. Create `Refund(order_id=order.id, amount=order.total)`.
2. Flush to obtain `refund.id` and `refund.created_at`.
3. Set `order.refunded_at = refund.created_at`.
4. Commit.
5. Return `RefundOut` (HTTP 201).

## Pydantic response model (src/api/routes/orders.py)

```python
class RefundOut(BaseModel):
    id: int
    order_id: int
    amount: int
    created_at: datetime
```

ISO-8601 serialization for `created_at` is Pydantic v2's default — no
custom formatter, intentionally avoiding the existing `"%Y-%d-%m"` quirk
in `OrderOut` (which is out of scope to fix here per constitution).
