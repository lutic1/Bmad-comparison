# Phase 1 — Data Model

## Changes summary

- **Modify** `Order`: add nullable `refunded_at` column.
- **Add** new `Refund` model + `refunds` table.

## `Order` (modified)

Located in `src/api/models.py`.

| Field         | Type                          | Constraints              | Notes                              |
|---------------|-------------------------------|--------------------------|------------------------------------|
| id            | int (PK)                      | existing                 | unchanged                          |
| user_id       | int (FK → users.id)           | existing, not null       | unchanged                          |
| total         | int                           | existing, not null       | integer cents, unchanged           |
| created_at    | datetime                      | existing, not null       | unchanged                          |
| **refunded_at** | datetime \| None             | **NEW**, nullable, default NULL | truthiness == "is refunded"; set in handler |

State transition: `refunded_at IS NULL` → `refunded_at = <utc now>` on
successful refund. No back-transition is exposed.

## `Refund` (new)

```python
class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), unique=True, nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    order: Mapped["Order"] = relationship()
```

| Field      | Type                  | Constraints                            | Notes                                |
|------------|-----------------------|----------------------------------------|--------------------------------------|
| id         | int (PK)              | autoincrement                          |                                      |
| order_id   | int (FK → orders.id)  | not null, **UNIQUE**                   | unique == "at most one refund per order" |
| amount     | int                   | not null                               | integer cents, snapshot of `Order.total` at refund time |
| created_at | datetime              | not null, default `datetime.utcnow`    | UTC, server-clock                    |

## Validation & invariants

- A `Refund` row exists ⇔ the referenced `Order.refunded_at IS NOT NULL`.
- `Refund.amount` is set to `Order.total` at the moment of refund (full
  refund only).
- The `UNIQUE` constraint on `refunds.order_id` is the authoritative
  enforcement of "at most one refund per order"; the handler also
  pre-checks for clearer error messages.

## Schema-creation note

The project creates the schema from `Base.metadata` at startup
(`src/api/main.py` `lifespan`). Per `CLAUDE.md`, the operator wipes
`app.db` between runs and migrations are intentionally not used —
adding the new column and table is therefore a no-cost change.
