# API Contract: POST /orders/{order_id}/refund

**Feature**: `001-order-refund`
**Date**: 2026-05-19

---

## Endpoint

`POST /orders/{order_id}/refund`

### Authentication

Required. Pass `X-User-Id: <integer>` header. The value must correspond to an existing user in the database. Returns **401** if absent or if the user does not exist.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `order_id` | integer | ID of the order to refund |

### Request Body

None.

---

## Responses

### 200 OK — Refund accepted

```json
{
  "order_id": 42,
  "refunded_at": "2026-05-19T14:30:00",
  "total": 1998
}
```

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | integer | The order that was refunded |
| `refunded_at` | string (ISO 8601) | UTC timestamp when the refund was recorded |
| `total` | integer | Order total in integer cents |

### 401 Unauthorized

Missing or invalid `X-User-Id` header.

```json
{"detail": "unauthorized"}
```

### 403 Forbidden

Order exists but belongs to a different user.

```json
{"detail": "forbidden"}
```

### 404 Not Found

No order with the given ID exists.

```json
{"detail": "order not found"}
```

### 409 Conflict

Order has already been refunded.

```json
{"detail": "order already refunded"}
```

### 422 Unprocessable Entity

Order is outside the 30-day refund window.

```json
{"detail": "refund window expired"}
```

---

## Check order (error precedence)

Checks are applied in this exact order:

1. Authentication — 401 if `X-User-Id` missing or user not found
2. Order existence — 404 if `order_id` not in database
3. Ownership — 403 if order belongs to a different user
4. Already refunded — 409 if `order.refunded` is `True`
5. 30-day window — 422 if `now_utc - order.created_at > timedelta(days=30)`
6. Accept and persist — 200 with `RefundOut`
