# Contract: `POST /orders/{order_id}/refund`

## Request

- **Method**: `POST`
- **Path**: `/orders/{order_id}/refund`
- **Path params**: `order_id: int` — id of the order to refund.
- **Headers**: `X-User-Id: int` — identifies the authenticated caller (per
  `api.deps.get_current_user`).
- **Body**: none.

## Successful response

- **Status**: `201 Created`
- **Content-Type**: `application/json`
- **Body** (`RefundOut`):

  ```json
  {
    "id": 7,
    "order_id": 42,
    "created_at": "2026-05-19T14:23:01"
  }
  ```

Side effects:

- A new row is inserted into `refunds`.
- The matching `orders.refunded_at` column is set to the same instant.

## Error responses

| Status | Detail (`detail` field) | Condition |
|--------|-------------------------|-----------|
| `401`  | `"missing X-User-Id header"` | `X-User-Id` header absent. |
| `401`  | `"unknown user"`             | `X-User-Id` does not match any `User`. |
| `404`  | `"order not found"`          | No `Order` with `id == order_id`. |
| `403`  | `"forbidden"`                | Order exists but `order.user_id != current_user.id`. |
| `400`  | `"refund window expired"`    | `now - order.created_at > 30 days`. |
| `409`  | `"order already refunded"`   | `order.refunded_at is not None`. |

Error responses never modify the database.

## Examples

### Happy path

```http
POST /orders/42/refund HTTP/1.1
X-User-Id: 1
```

```http
HTTP/1.1 201 Created
Content-Type: application/json

{"id": 7, "order_id": 42, "created_at": "2026-05-19T14:23:01"}
```

### Window expired

```http
POST /orders/42/refund HTTP/1.1
X-User-Id: 1
```

(`orders.created_at` was 31 days ago)

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{"detail": "refund window expired"}
```

### Already refunded

```http
POST /orders/42/refund HTTP/1.1
X-User-Id: 1
```

(`orders.refunded_at` is already set)

```http
HTTP/1.1 409 Conflict
Content-Type: application/json

{"detail": "order already refunded"}
```
