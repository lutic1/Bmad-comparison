# Quickstart: Discount Codes at Checkout

Validate the feature end-to-end after implementation.

## Prerequisites

```bash
# From repo root
pip install -e ".[dev]"     # or however the project installs
pytest                      # must be green before starting
```

## 1. Start the server

```bash
uvicorn src.api.main:app --reload
```

Seeded codes are inserted on startup: `SAVE5`, `SAVE10`, `SAVE20`.

## 2. Create a user

```bash
curl -s -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "name": "Test User"}' | python3 -m json.tool
# Note the returned "id" — use it as USER_ID below
```

## 3. Checkout without a discount code (regression check)

```bash
curl -s -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"items": [{"sku": "WIDGET", "quantity": 2, "unit_price": 9.99}]}' \
  | python3 -m json.tool
# Expected: total=1998, discount_code=null
```

## 4. Checkout with a 10% discount code

```bash
curl -s -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"items": [{"sku": "WIDGET", "quantity": 2, "unit_price": 9.99}], "discount_code": "SAVE10"}' \
  | python3 -m json.tool
# Expected: total=1798 (1998 - 10%), discount_code="SAVE10"
```

## 5. Verify case-insensitivity

```bash
curl -s -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"items": [{"sku": "WIDGET", "quantity": 1, "unit_price": 10.00}], "discount_code": "save20"}' \
  | python3 -m json.tool
# Expected: total=800 (1000 - 20%), discount_code="SAVE20"
```

## 6. Verify invalid code rejection

```bash
curl -s -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"items": [{"sku": "WIDGET", "quantity": 1, "unit_price": 10.00}], "discount_code": "BOGUS"}' \
  | python3 -m json.tool
# Expected: HTTP 422, detail="Invalid discount code"
```

## 7. Run the test suite

```bash
pytest tests/test_orders.py -v
# All existing tests must still pass; new discount tests must pass
```
