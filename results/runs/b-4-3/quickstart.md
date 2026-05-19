# Quickstart: Checkout Discount Code

Validate the feature end-to-end using `curl` against a running local server (`uvicorn src.api.main:app`).

## Prerequisites

- Server running on `http://localhost:8000`
- Fresh `app.db` (wipe if upgrading from a previous schema)
- Seed codes `SAVE5`, `SAVE10`, `SAVE20` are loaded automatically at startup

---

## Step 1 — Create a user

```bash
curl -s -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "name": "Alice"}' | python3 -m json.tool
```

Note the returned `id` (e.g., `1`). Use it as `USER_ID` below.

---

## Step 2 — Create an order

```bash
curl -s -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{
    "items": [
      {"sku": "WIDGET-A", "quantity": 2, "unit_price": 5.00}
    ]
  }' | python3 -m json.tool
```

Expected: order with `total: 1000` (2 × $5.00 = $10.00 = 1000 cents). Note the `id` (e.g., `1`).

---

## Step 3 — Apply a 10% discount code

```bash
curl -s -X POST http://localhost:8000/orders/1/discount-code \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"code": "SAVE10"}' | python3 -m json.tool
```

Expected response:
```json
{
  "id": 1,
  "total": 900,
  "discount_code": "SAVE10",
  "discount_amount_cents": 100,
  ...
}
```

---

## Step 4 — Apply a different code (replacement)

```bash
curl -s -X POST http://localhost:8000/orders/1/discount-code \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"code": "SAVE20"}' | python3 -m json.tool
```

Expected: `total: 800`, `discount_code: "SAVE20"`, `discount_amount_cents: 200` (20% of original 1000).

---

## Step 5 — Remove the discount

```bash
curl -s -X DELETE http://localhost:8000/orders/1/discount-code \
  -H "X-User-Id: 1" | python3 -m json.tool
```

Expected: `total: 1000`, `discount_code: null`, `discount_amount_cents: 0`.

---

## Step 6 — Verify invalid code is rejected

```bash
curl -s -X POST http://localhost:8000/orders/1/discount-code \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"code": "FAKECODE"}' | python3 -m json.tool
```

Expected: `422` with `{"detail": "invalid discount code"}`.

---

## Step 7 — Run the test suite

```bash
pytest tests/test_discounts.py -v
```

All tests should pass. To run the full suite:

```bash
pytest
```
