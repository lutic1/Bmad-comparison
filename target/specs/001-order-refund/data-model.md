# Phase 1 Data Model — Order Refund

## Changes to existing entities

### `Order` (existing — additive change)

| Column        | Type             | Constraints                  | Notes |
|---------------|------------------|------------------------------|-------|
| `refunded_at` | `DateTime` (UTC) | NULL allowed; default `NULL` | Set to `datetime.utcnow()` when the order is refunded. `NULL` means the order has not been refunded. |

State transitions:

- `refunded_at IS NULL` → `refunded_at = <utcnow>`: occurs exactly once
  per order, on a successful refund.
- The reverse transition does not exist in this feature.

## New entities

### `Refund`

| Column       | Type                | Constraints                                 | Notes |
|--------------|---------------------|---------------------------------------------|-------|
| `id`         | `Integer`           | PRIMARY KEY                                 | Autoincrement. |
| `order_id`   | `Integer`           | FOREIGN KEY → `orders.id`, NOT NULL, UNIQUE | UNIQUE enforces "at most one refund per order" at the DB level. |
| `amount`     | `Integer`           | NOT NULL                                    | Stored as integer cents, mirroring `Order.total`. Equal to `order.total` at refund time. |
| `created_at` | `DateTime` (UTC)    | NOT NULL, default `datetime.utcnow`         | Time the refund was issued. |

Relationships:

- `Refund.order` ↔ `Order.refund` (one-to-one; back-populated).

## Validation rules (enforced in the route handler)

- The caller must be authenticated (401 otherwise — enforced by
  `get_current_user`).
- The order must exist (404 otherwise).
- The order must belong to the authenticated user (403 otherwise).
- `datetime.utcnow() - order.created_at <= timedelta(days=30)` (400 with
  `"refund window expired"` otherwise).
- The order must not already be refunded — i.e., `order.refunded_at IS
  NULL` (409 with `"order already refunded"` otherwise). The UNIQUE
  constraint on `refunds.order_id` provides a backstop under
  concurrency.

## Lifecycle summary

```text
[Order created] ──(within 30 days, owner, not refunded)──▶ [Refund row created]
                                                            └─ Order.refunded_at = now
```
