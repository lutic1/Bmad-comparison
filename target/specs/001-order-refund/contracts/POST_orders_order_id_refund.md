# Contract: POST /orders/{order_id}/refund

**Feature**: `001-order-refund`
**Date**: 2026-05-19

---

## Endpoint

```
POST /orders/{order_id}/refund
```

---

## Authentication

Required. Pass the authenticated user's ID in the `X-User-Id` header.

| Header       | Type    | Required | Description              |
|--------------|---------|----------|--------------------------|
| `X-User-Id`  | integer | Yes      | ID of the requesting user |

---

## Path Parameters

| Parameter  | Type    | Required | Description           |
|------------|---------|----------|-----------------------|
| `order_id` | integer | Yes      | ID of the order to refund |

---

## Request Body

None.

---

## Success Response

**HTTP 200 OK**

```json
{
  "order_id": 42,
  "refunded": true,
  "refunded_at": "2026-19-05"
}
```

| Field         | Type    | Description                                      |
|---------------|---------|--------------------------------------------------|
| `order_id`    | integer | The refunded order's identifier                  |
| `refunded`    | boolean | Always `true` on a successful refund             |
| `refunded_at` | string  | Refund timestamp, formatted `%Y-%d-%m`           |

---

## Error Responses

| Status | Condition                                    | Detail message                      |
|--------|----------------------------------------------|-------------------------------------|
| 401    | `X-User-Id` header absent                   | `"missing X-User-Id header"`        |
| 401    | `X-User-Id` refers to a non-existent user   | `"unknown user"`                    |
| 404    | `order_id` not found in database            | `"order not found"`                 |
| 404    | Order exists but belongs to a different user | `"order not found"`                 |
| 422    | Order was created more than 30 days ago     | `"refund window has expired"`       |
| 422    | Order has already been refunded             | `"order has already been refunded"` |

All error bodies follow the FastAPI default `{"detail": "<message>"}` shape.

---

## Business Rules

1. Authentication is checked before any database lookup.
2. The order must exist AND belong to the authenticated user; both failure
   conditions return 404 to prevent ownership disclosure.
3. The refund window is `order.created_at + 30 days >= request time` (inclusive).
4. An order can only be refunded once; a second request is a 422 error.
5. On success, `Order.refunded` is set to `True` and `Order.refunded_at` is set
   to the current UTC time.
