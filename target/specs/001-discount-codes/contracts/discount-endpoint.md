# Contract: Apply Discount Code to Order

## Endpoint

```
POST /orders/{order_id}/discount
```

## Auth

- Requires `X-User-Id` header (existing `get_current_user` dependency).
- The order at `{order_id}` MUST belong to that user.

## Valid codes

Module-level mapping in `src/api/routes/orders.py`:

```python
DISCOUNT_CODES: dict[str, int] = {
    "SAVE5": 5,
    "SAVE10": 10,
    "SAVE20": 20,
}
```

Lookup is case-insensitive (input is uppercased before lookup).

## Request

Content-Type: `application/json`

```json
{
  "code": "SAVE10"
}
```

| Field | Type   | Required | Notes                                                    |
|-------|--------|----------|----------------------------------------------------------|
| code  | string | yes      | Non-empty. Case-insensitive. Must resolve to a known code. |

## Response — 200 OK

Same shape as the existing `OrderOut` model, with two additional
optional fields surfaced when a discount is present:

```json
{
  "id": 42,
  "user_id": 7,
  "subtotal": 10000,
  "discount_code": "SAVE10",
  "total": 9000,
  "created_at": "2026-19-05",
  "items": [
    {"sku": "WIDGET", "quantity": 2, "unit_price": 5000}
  ]
}
```

- `subtotal` and `total` are integer cents.
- `discount_code` is the canonical uppercased code.
- `created_at` preserves the existing `%Y-%d-%m` format from
  `routes/orders.py` (unrelated; not changed by this feature).

## Error responses

| Status | Condition                                                        | Body                                              |
|--------|------------------------------------------------------------------|---------------------------------------------------|
| 400    | `code` missing, empty, or not a key of `DISCOUNT_CODES`          | `{"detail": "invalid discount code"}`             |
| 401    | `X-User-Id` header missing or references unknown user             | `{"detail": "missing X-User-Id header"}` / `"unknown user"` (existing) |
| 403    | Order exists but belongs to a different user                     | `{"detail": "forbidden"}`                         |
| 404    | No order with the given `order_id`                                | `{"detail": "order not found"}`                   |

## Behaviour

1. Resolve the order; 404 if missing, 403 if not owned by the caller.
2. Validate `code`; 400 on any failure.
3. If `order.subtotal IS NULL`, set `order.subtotal = order.total`
   (snapshot of the pre-discount total).
4. Compute `discount_cents = (order.subtotal * pct + 50) // 100` and
   `order.total = order.subtotal - discount_cents`.
5. Set `order.discount_code = code.upper()`.
6. Commit and return the updated order.

Repeat calls on the same order replace the discount; step 3 only runs
the first time (subtotal already snapshotted), so subsequent
percentages are always computed against the original subtotal.

## Examples

| subtotal_cents | code    | discount_cents | total_cents |
|----------------|---------|----------------|-------------|
| 10000          | SAVE5   | 500            | 9500        |
| 10000          | SAVE10  | 1000           | 9000        |
| 10000          | SAVE20  | 2000           | 8000        |
| 5000           | SAVE20  | 1000           | 4000        |
| 999            | SAVE10  | 100            | 899         |
| 0              | SAVE10  | 0              | 0           |
