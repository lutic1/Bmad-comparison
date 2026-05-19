# API Contracts: Orders

**Feature**: 001-fix-order-date-format
**Date**: 2026-05-19

Only the `created_at` field contract changes. All other fields are unchanged.

---

## POST /orders

Creates a new order for the authenticated user.

**Request headers**: `X-User-Id: <user_id>` (required)

**Request body**:
```json
{
  "items": [
    { "sku": "string", "quantity": 1, "unit_price": 9.99 }
  ]
}
```

**Response 201**:
```json
{
  "id": 1,
  "user_id": 1,
  "total": 999,
  "created_at": "2026-05-19",
  "items": [
    { "sku": "WIDGET", "quantity": 1, "unit_price": 999 }
  ]
}
```

**`created_at` contract**: ISO 8601 date string, format `YYYY-MM-DD`.
Year is first, month is second, day is third.

---

## GET /orders/{order_id}

Returns a single order owned by the authenticated user.

**Request headers**: `X-User-Id: <user_id>` (required)

**Response 200**:
```json
{
  "id": 1,
  "user_id": 1,
  "total": 999,
  "created_at": "2026-05-19",
  "items": [
    { "sku": "WIDGET", "quantity": 1, "unit_price": 999 }
  ]
}
```

**`created_at` contract**: Same as POST — ISO 8601 date string `YYYY-MM-DD`.

**Response 403**: Returned when the requesting user does not own the order.

**Response 404**: Returned when the order does not exist.
