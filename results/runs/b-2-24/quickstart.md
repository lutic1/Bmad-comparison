# Quickstart: Order Refund

**Feature**: `001-order-refund`

## Prerequisites

- Python 3.11+
- Service running: `uvicorn api.main:app --reload`
- A user and an order already exist (see steps 1–2 below)

---

## Happy path walkthrough

```bash
# 1. Create a user
curl -s -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","name":"Alice"}' | python3 -m json.tool
# Note the returned "id", e.g. 1

# 2. Create an order
curl -s -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"items":[{"sku":"WIDGET","quantity":2,"unit_price":9.99}]}' | python3 -m json.tool
# Note the returned "id", e.g. 1

# 3. Request a refund
curl -s -X POST http://localhost:8000/orders/1/refund \
  -H "X-User-Id: 1" | python3 -m json.tool
# Expected 200: {"order_id":1,"refunded_at":"...","total":1998}

# 4. Try to refund again (idempotency check)
curl -s -X POST http://localhost:8000/orders/1/refund \
  -H "X-User-Id: 1" | python3 -m json.tool
# Expected 409: {"detail":"order already refunded"}
```

---

## Error path validation

```bash
# Unauthenticated
curl -s -X POST http://localhost:8000/orders/1/refund
# Expected 401

# Wrong user (create a second user first, id=2)
curl -s -X POST http://localhost:8000/orders/1/refund -H "X-User-Id: 2"
# Expected 403

# Non-existent order
curl -s -X POST http://localhost:8000/orders/9999/refund -H "X-User-Id: 1"
# Expected 404
```

---

## Run the test suite

```bash
pytest tests/test_refund.py -v
```
