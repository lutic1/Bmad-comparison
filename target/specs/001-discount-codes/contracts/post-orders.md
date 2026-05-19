# Contract: POST /orders

**Change type**: Additive (backwards-compatible)

---

## Request

```
POST /orders
X-User-Id: <user_id>
Content-Type: application/json
```

### Body (updated)

```json
{
  "items": [
    {
      "sku":        "string (required)",
      "quantity":   "integer ≥ 1 (required)",
      "unit_price": "number in dollars, e.g. 9.99 (required)"
    }
  ],
  "discount_code": "string | null (optional, case-insensitive)"
}
```

`discount_code` is **optional**. Omitting it or passing `null` is equivalent
to no discount.

---

## Responses

### 201 Created — no discount

```json
{
  "id":            1,
  "user_id":       42,
  "total":         1998,
  "discount_code": null,
  "created_at":    "2026-19-05",
  "items": [
    { "sku": "WIDGET", "quantity": 2, "unit_price": 999 }
  ]
}
```

### 201 Created — with valid discount code

```json
{
  "id":            2,
  "user_id":       42,
  "total":         1798,
  "discount_code": "SAVE10",
  "created_at":    "2026-19-05",
  "items": [
    { "sku": "WIDGET", "quantity": 2, "unit_price": 999 }
  ]
}
```

`total` is the post-discount amount in cents. `discount_code` echoes back
the normalised (uppercase) code that was applied.

### 401 Unauthorised — missing or invalid `X-User-Id`

```json
{ "detail": "Unauthorised" }
```

### 400 Bad Request — empty items list

```json
{ "detail": "Order must contain at least one item" }
```

### 422 Unprocessable Entity — unrecognised discount code

```json
{ "detail": "Invalid discount code" }
```

### 422 Unprocessable Entity — blank discount code string

```json
{ "detail": "..." }
```

FastAPI's standard schema-validation 422 is returned for a blank string if
a `min_length=1` constraint is applied; otherwise the route handler returns
its own 422 with `"Invalid discount code"`.

---

## No-change endpoints

`GET /orders/{order_id}` response shape gains the `discount_code` field
(nullable) as an additive, backwards-compatible change. No other behaviour
changes.
