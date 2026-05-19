# Contract: Order Response

**Feature**: `001-fix-order-date-format`
**Date**: 2026-05-18

## Endpoints

### POST /orders

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

**Response** `201 Created`:
```json
{
  "id": 1,
  "user_id": 1,
  "total": 999,
  "created_at": "2026-05-18",
  "items": [
    { "sku": "WIDGET", "quantity": 1, "unit_price": 999 }
  ]
}
```

---

### GET /orders/{order_id}

Retrieves an order owned by the authenticated user.

**Request headers**: `X-User-Id: <int>`

**Response** `200 OK`:
```json
{
  "id": 1,
  "user_id": 1,
  "total": 999,
  "created_at": "2026-05-18",
  "items": [
    { "sku": "WIDGET", "quantity": 1, "unit_price": 999 }
  ]
}
```

---

## Field Notes

| Field | Type | Format | Notes |
|-------|------|--------|-------|
| `created_at` | string | `YYYY-MM-DD` (ISO 8601) | Bug fix: was incorrectly `YYYY-DD-MM` |
| `total` | integer | cents | Stored and returned as integer cents |
| `unit_price` | integer | cents | Same as total |

---

## Error Responses

| Status | Condition |
|--------|-----------|
| 400 | `items` array is empty |
| 401 | `X-User-Id` header missing or user not found |
| 403 | Authenticated user does not own the requested order |
| 404 | Order ID does not exist |
