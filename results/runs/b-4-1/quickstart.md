# Quickstart: Discount Code at Checkout

**Feature**: 001-discount-codes
**Date**: 2026-05-18

Minimal walkthrough to manually verify the feature end-to-end after
implementation.

---

## Prerequisites

```bash
# From repo root — wipe stale DB (schema will be re-created on startup)
rm -f app.db
uvicorn src.api.main:app --reload
```

---

## Step 1: Create a user

```bash
curl -s -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "name": "Alice"}' | python3 -m json.tool
# Note the returned "id" (e.g. 1)
```

---

## Step 2: Create an order

```bash
curl -s -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{
    "items": [
      {"sku": "WIDGET-A", "quantity": 2, "unit_price": 50.00}
    ]
  }' | python3 -m json.tool
# Expect total = 10000 (cents). Note the returned "id" (e.g. 1)
```

---

## Step 3: Seed a discount code (via Python REPL or test fixture)

There is no admin endpoint for creating discount codes in this feature.
Seed one directly:

```python
# python3 -c "..."
from src.api.deps import SessionLocal
from src.api.models import DiscountCode

db = SessionLocal()
db.add(DiscountCode(code="SAVE10", percentage=10, is_active=True))
db.commit()
db.close()
```

---

## Step 4: Apply the discount

```bash
curl -s -X POST http://localhost:8000/orders/1/apply-discount \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"code": "save10"}' | python3 -m json.tool
```

**Expected response** (values in cents):

```json
{
  "id": 1,
  "user_id": 1,
  "subtotal": 10000,
  "discount_code": "SAVE10",
  "discount_percentage": 10,
  "discount_amount": 1000,
  "final_total": 9000,
  "items": [...],
  "created_at": "..."
}
```

---

## Step 5: Verify error paths

```bash
# Invalid code
curl -s -X POST http://localhost:8000/orders/1/apply-discount \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"code": "BADCODE"}' | python3 -m json.tool
# Expect 400 {"detail": "Invalid discount code"}

# Duplicate application
curl -s -X POST http://localhost:8000/orders/1/apply-discount \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"code": "SAVE10"}' | python3 -m json.tool
# Expect 400 {"detail": "A discount has already been applied to this order"}
```

---

## Step 6: Run the test suite

```bash
pytest tests/test_orders.py -v
# All discount-related tests should pass; existing tests must not regress
```
