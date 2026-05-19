# Data Model — Order Refund Endpoint

## Changes to `Order` (`src/api/models.py`)

Add one nullable column:

| Field | Type | Nullable | Default | Notes |
|-------|------|----------|---------|-------|
| `refunded_at` | `datetime` | yes | `None` | Set to `datetime.utcnow()` at the moment the refund is recorded. `None` means "not refunded". |

No other `Order` fields change.

## New entity: `Refund`

`__tablename__ = "refunds"`

| Field | Type | Nullable | Default | Notes |
|-------|------|----------|---------|-------|
| `id` | `int` | no | autoincrement | Primary key. |
| `order_id` | `int` | no | — | `ForeignKey("orders.id")`, `unique=True` (enforces one refund per order at the DB layer in addition to the application-level check). |
| `created_at` | `datetime` | no | `datetime.utcnow` | When the refund was recorded. |

Relationships:

- `Refund.order: Mapped[Order]` — many-to-one (effectively one-to-one via
  `unique=True`).
- `Order.refund: Mapped["Refund | None"]` — back-populates the above.

## Validation rules (enforced in the route, not at the DB layer)

- The authenticated user must equal `order.user_id` (FR-003).
- `datetime.utcnow() - order.created_at <= timedelta(days=30)` (FR-004).
- `order.refunded_at` must be `None` at the time of the request (FR-005).

## State transitions

`Order` has two refund-related states:

```text
not refunded  ──(successful refund request)──>  refunded
```

The transition is one-way. There is no "unrefund" operation in this feature.

## Migrations

None. `Base.metadata.create_all` at app startup creates the new column and
table. Per `CLAUDE.md`, the operator wipes `app.db` between runs.
