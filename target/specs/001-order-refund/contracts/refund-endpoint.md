# Contract: `POST /orders/{order_id}/refund`

## Request

- **Method**: `POST`
- **Path**: `/orders/{order_id}/refund`
- **Path params**:
  - `order_id` *(int, required)* — id of the order to refund.
- **Headers**:
  - `X-User-Id: <int>` *(required)* — identifies the requesting user
    (existing auth scheme; see `api.deps.get_current_user`).
- **Body**: none.

## Response — Success (201 Created)

```json
{
  "id": 42,
  "order_id": 17,
  "amount": 12999,
  "created_at": "2026-05-19T14:23:01.234567"
}
```

| Field      | Type           | Notes                                          |
|------------|----------------|------------------------------------------------|
| id         | integer        | id of the newly created refund record          |
| order_id   | integer        | id of the order that was refunded              |
| amount     | integer        | integer cents, snapshot of `Order.total`       |
| created_at | string (ISO-8601 datetime) | UTC, server clock                  |

**Side effect**: The corresponding `Order.refunded_at` is set to the same
timestamp as the refund's `created_at`.

## Response — Errors

| Status | Detail                                  | When                                                                 |
|--------|-----------------------------------------|----------------------------------------------------------------------|
| 401    | `missing X-User-Id header` / `unknown user` | `X-User-Id` header missing or refers to a user that does not exist. (Handled by `get_current_user`.) |
| 404    | `order not found`                        | Order id does not exist, OR order exists but belongs to a different user (non-disclosure per FR-003). |
| 400    | `refund window expired`                  | `(now - order.created_at) > 30 days`.                                |
| 409    | `order already refunded`                 | A refund already exists for this order (pre-check OR `IntegrityError` from unique constraint). |

All error responses use FastAPI's default error shape:
`{"detail": "<message>"}`.

## Behavior summary

1. Resolve `current_user` via `get_current_user`. → 401 on failure.
2. Look up `Order` by `order_id`. If missing OR `order.user_id != current_user.id`, return **404**.
3. If `(datetime.utcnow() - order.created_at) > timedelta(days=30)`, return **400**.
4. If `order.refunded_at is not None`, return **409**.
5. Create `Refund(order_id=order.id, amount=order.total)`; flush; set `order.refunded_at = refund.created_at`; commit.
6. If the commit raises `IntegrityError` on the unique-on-`order_id` constraint (concurrent racer beat us), return **409**.
7. Return `RefundOut` from the persisted `Refund`.
