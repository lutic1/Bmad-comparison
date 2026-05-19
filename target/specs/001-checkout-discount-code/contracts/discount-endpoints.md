# API Contracts: Discount Code Endpoints

All endpoints are authenticated via the `X-User-Id` header (same as existing order endpoints).
Ownership is enforced: the authenticated user must own the target order.

---

## POST /orders/{order_id}/discount-code

Apply a discount code to an order. If another code is already applied, it is replaced atomically.

### Request

**Headers**
```
X-User-Id: <integer>   (required)
Content-Type: application/json
```

**Path parameters**
| Name      | Type | Required | Description   |
|-----------|------|----------|---------------|
| order_id  | int  | Yes      | Order to discount |

**Body**
```json
{
  "code": "SAVE10"
}
```

| Field | Type   | Required | Constraints                | Notes                        |
|-------|--------|----------|----------------------------|------------------------------|
| code  | string | Yes      | Non-empty                  | Case-insensitive; normalized to uppercase |

### Responses

**200 OK** — Discount applied (or replaced). Returns updated order.
```json
{
  "id": 42,
  "user_id": 7,
  "total": 900,
  "discount_code": "SAVE10",
  "discount_amount_cents": 100,
  "created_at": "2026-19-05",
  "items": [
    { "sku": "WIDGET", "quantity": 1, "unit_price": 1000 }
  ]
}
```

**401 Unauthorized** — Missing or invalid `X-User-Id` header.
```json
{ "detail": "unauthorized" }
```

**403 Forbidden** — Authenticated user does not own the order.
```json
{ "detail": "forbidden" }
```

**404 Not Found** — Order does not exist.
```json
{ "detail": "order not found" }
```

**422 Unprocessable Entity** — Discount code is not recognized.
```json
{ "detail": "invalid discount code" }
```

---

## DELETE /orders/{order_id}/discount-code

Remove the currently applied discount code from an order, restoring the original total.

### Request

**Headers**
```
X-User-Id: <integer>   (required)
```

**Path parameters**
| Name      | Type | Required | Description              |
|-----------|------|----------|--------------------------|
| order_id  | int  | Yes      | Order to remove discount from |

**Body**: None

### Responses

**200 OK** — Discount removed. Returns updated order with restored total.
```json
{
  "id": 42,
  "user_id": 7,
  "total": 1000,
  "discount_code": null,
  "discount_amount_cents": 0,
  "created_at": "2026-19-05",
  "items": [
    { "sku": "WIDGET", "quantity": 1, "unit_price": 1000 }
  ]
}
```

**400 Bad Request** — No discount code is currently applied to this order.
```json
{ "detail": "no discount code applied" }
```

**401 Unauthorized** — Missing or invalid `X-User-Id` header.
```json
{ "detail": "unauthorized" }
```

**403 Forbidden** — Authenticated user does not own the order.
```json
{ "detail": "forbidden" }
```

**404 Not Found** — Order does not exist.
```json
{ "detail": "order not found" }
```

---

## Business Rules Summary

| Rule                              | Enforcement Point         |
|-----------------------------------|---------------------------|
| Code must exist in discount_codes | POST handler, 422          |
| Only one active code per order    | POST handler replaces silently |
| Removal requires an active code   | DELETE handler, 400        |
| User must own the order           | Both handlers, 403         |
| Discount computed on current total| POST handler (post-restoration if replacing) |
| Total never goes negative         | Capped at 0 (consistent with adjust_total) |
