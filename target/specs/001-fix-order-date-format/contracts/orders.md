# API Contract: Orders

**Feature**: 001-fix-order-date-format
**Date**: 2026-05-18

## POST /orders

Creates a new order for the authenticated user.

**Request headers**: `X-User-Id: <int>`

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
  "user_id": 42,
  "total": 999,
  "created_at": "2025-03-07",
  "items": [
    { "sku": "ABC", "quantity": 1, "unit_price": 999 }
  ]
}
```

**`created_at` format**: `YYYY-MM-DD` (ISO 8601 date). Previously this field
incorrectly returned `YYYY-DD-MM`; the bug fix corrects it to `YYYY-MM-DD`.

**Error responses**:
- `400 Bad Request` — empty items list
- `401 Unauthorized` — missing or invalid `X-User-Id`

---

## GET /orders/{order_id}

Retrieves a single order by ID for the authenticated user.

**Request headers**: `X-User-Id: <int>`

**Response 200**:
```json
{
  "id": 1,
  "user_id": 42,
  "total": 999,
  "created_at": "2025-03-07",
  "items": [
    { "sku": "ABC", "quantity": 1, "unit_price": 999 }
  ]
}
```

**`created_at` format**: `YYYY-MM-DD` (ISO 8601 date), same correction as
POST /orders above.

**Error responses**:
- `401 Unauthorized` — missing or invalid `X-User-Id`
- `403 Forbidden` — order belongs to a different user
- `404 Not Found` — order does not exist
