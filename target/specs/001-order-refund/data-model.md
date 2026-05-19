# Data Model: Order Refund

**Feature**: `001-order-refund`
**Date**: 2026-05-18

## Model Changes

### Order (existing — two fields added)

| Field         | Type              | Nullable | Default | Notes                                          |
|---------------|-------------------|----------|---------|------------------------------------------------|
| id            | int               | no       | PK      | existing                                       |
| user_id       | int (FK → users)  | no       | —       | existing                                       |
| total         | int (cents)       | no       | —       | existing                                       |
| created_at    | datetime          | no       | utcnow  | existing                                       |
| **refunded**  | bool              | no       | False   | **NEW** — true once a refund is processed      |
| **refunded_at** | datetime        | yes      | None    | **NEW** — UTC timestamp of refund; null until refunded |

No other models are created or modified.

## Pydantic Response Model (new)

### RefundOut

Returned by `POST /orders/{order_id}/refund` on success.

| Field        | Type     | Notes                                      |
|--------------|----------|--------------------------------------------|
| order_id     | int      | The refunded order's ID                    |
| refunded_at  | datetime | UTC timestamp recorded at refund time      |
| amount       | int      | Refunded amount in cents (= order total)   |

## State Transitions

```
Order state machine (refunded field):

  [refunded=False]
        |
        | POST /orders/{id}/refund (valid request)
        ↓
  [refunded=True, refunded_at=<timestamp>]
        |
        | (terminal — no further transitions)
```

Attempting the transition from `[refunded=True]` returns 422.

## Validation Rules

| Rule                        | Checked against       | Error   |
|-----------------------------|-----------------------|---------|
| User authenticated          | X-User-Id header      | 401     |
| Order exists                | orders table          | 404     |
| Order owned by caller       | order.user_id         | 403     |
| order.refunded == False     | refunded field        | 422     |
| age ≤ 30 days (inclusive)   | created_at vs utcnow  | 422     |

Validation is applied in the order listed above.

## Schema Note

The project uses SQLAlchemy's `Base.metadata.create_all()` at startup with no migrations. Adding columns to `Order` requires wiping `app.db` between runs in development. Tests are unaffected (in-memory SQLite recreated per test).
