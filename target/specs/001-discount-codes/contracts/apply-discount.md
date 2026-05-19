# Contract: Apply Discount Code

**Endpoint**: `POST /orders/{order_id}/apply-discount`
**Router**: `src/api/routes/orders.py`
**Auth**: Required — `X-User-Id` header (must be the order owner)

---

## Request

### Path Parameters

| Parameter  | Type | Required | Description     |
|-----------|------|----------|-----------------|
| `order_id` | int  | Yes      | ID of the order |

### Headers

| Header      | Type | Required | Description             |
|------------|------|----------|-------------------------|
| `X-User-Id` | int  | Yes      | ID of the current user  |

### Body (JSON)

```json
{
  "code": "SAVE10"
}
```

| Field  | Type   | Required | Constraints                          |
|--------|--------|----------|--------------------------------------|
| `code` | string | Yes      | Trimmed, uppercased before validation |

---

## Responses

### 200 OK — Discount applied

```json
{
  "id": 1,
  "user_id": 1,
  "subtotal": 10000,
  "discount_code": "SAVE10",
  "discount_percentage": 10,
  "discount_amount": 1000,
  "final_total": 9000,
  "items": [
    {
      "id": 1,
      "sku": "WIDGET-A",
      "quantity": 2,
      "unit_price": 5000
    }
  ],
  "created_at": "2026-18-05"
}
```

All monetary values are in **cents** (integer).

| Field                | Type        | Description                              |
|---------------------|------------|------------------------------------------|
| `id`                | int         | Order ID                                 |
| `user_id`           | int         | Owning user ID                           |
| `subtotal`          | int         | Original order total (cents)             |
| `discount_code`     | string      | The applied code (uppercase)             |
| `discount_percentage` | int       | 5, 10, or 20                             |
| `discount_amount`   | int         | `round(subtotal * percentage / 100)`     |
| `final_total`       | int         | `subtotal - discount_amount`             |
| `items`             | array       | Order line items                         |
| `created_at`        | string      | ISO-ish date string                      |

### 400 Bad Request — Invalid code

```json
{"detail": "Invalid discount code"}
```

### 400 Bad Request — Inactive code

```json
{"detail": "Discount code is no longer active"}
```

### 400 Bad Request — Discount already applied

```json
{"detail": "A discount has already been applied to this order"}
```

### 401 Unauthorized — Missing or invalid X-User-Id

```json
{"detail": "Not authenticated"}
```

### 403 Forbidden — User does not own the order

```json
{"detail": "Forbidden"}
```

### 404 Not Found — Order does not exist

```json
{"detail": "Order not found"}
```

---

## Behaviour Notes

- `code` is normalised (`strip().upper()`) before lookup.
- Lookup checks both existence **and** `is_active == True`; the
  two conditions produce distinct error messages.
- A second call with any code on an order that already has a
  `discount_code_id` returns 400 immediately, before code lookup.
- `discount_amount` is rounded to the nearest cent (integer division
  consistent with cents-based storage).
