# Phase 1 Data Model: Order Refund

Two changes to `src/api/models.py`: a new column on `Order` and a new
`Refund` table. No migration is required (CLAUDE.md: schema is created
from `Base.metadata` at startup; the operator wipes `app.db` between
runs).

## Modified: `Order`

| Column        | Type                                  | Notes |
|---------------|---------------------------------------|-------|
| `id`          | `int`, PK                             | unchanged |
| `user_id`     | `int`, FK → `users.id`, NOT NULL      | unchanged |
| `total`       | `int` (cents), NOT NULL               | unchanged |
| `created_at`  | `datetime`, default `utcnow`, NOT NULL | unchanged |
| **`refunded_at`** | **`datetime`, NULLABLE**          | **NEW.** `NULL` ⇒ not refunded; non-null ⇒ refund timestamp |

Validation / invariants:

- `refunded_at` is set exactly once, by the refund route, and is never
  cleared.
- `refunded_at IS NOT NULL` ⇔ a `Refund` row exists with this
  `order_id`.

## New: `Refund`

```text
__tablename__ = "refunds"
```

| Column        | Type                                       | Notes |
|---------------|--------------------------------------------|-------|
| `id`          | `int`, PK                                  | autoincrement |
| `order_id`    | `int`, FK → `orders.id`, **UNIQUE**, NOT NULL | unique enforces "one refund per order" at the DB level |
| `amount`      | `int` (cents), NOT NULL                    | snapshot of `Order.total` at refund time |
| `created_at`  | `datetime`, default `utcnow`, NOT NULL     | when the refund was issued |

Relationships:

- `Refund.order: Mapped[Order] = relationship(...)` — optional; the
  route does not need it. Adding it keeps `Refund` symmetric with the
  rest of the file but is not required for correctness. Decision: add
  it for consistency.
- `Order.refund: Mapped["Refund | None"] = relationship(back_populates="order", uselist=False)` —
  add the inverse so callers can navigate from an order to its refund
  if needed. Not required by FR-* but cheap and consistent with the
  existing `Order.items` / `Order.user` patterns.

Validation rules (enforced in the route, not the schema):

- The caller must own the order (`order.user_id == current_user.id`).
- `datetime.utcnow() - order.created_at <= timedelta(days=30)`.
- `order.refunded_at IS NULL` at the start of the request.

State transitions:

```text
(not refunded)  --POST /orders/{id}/refund (eligible)-->  (refunded)
(refunded)      --POST /orders/{id}/refund-->  rejected (409, no transition)
```

There is no "un-refund" transition.

## Entities recap

- **Order**: gains `refunded_at` (nullable timestamp) and an optional
  inverse `refund` relationship.
- **Refund**: new entity, one-per-order, snapshot of the refunded
  amount with the time of issue.
