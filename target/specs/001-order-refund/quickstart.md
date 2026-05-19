# Quickstart: Order Refund

**Date**: 2026-05-19

Verify the refund endpoint end-to-end using `curl` against a running local server.

---

## Prerequisites

```bash
# Install dependencies and start the server
pip install -e .
uvicorn src.api.main:app --reload
```

---

## 1. Create a user

```bash
curl -s -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice"}' | python3 -m json.tool
# → {"id": 1, "name": "Alice"}
```

## 2. Create an order

```bash
curl -s -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"items": [{"sku": "WIDGET-01", "quantity": 2, "unit_price": 999}]}' \
  | python3 -m json.tool
# → {"id": 1, "user_id": 1, "total": 1998, "created_at": "...", "items": [...]}
```

## 3. Request a refund (happy path)

```bash
curl -s -X POST http://localhost:8000/orders/1/refund \
  -H "X-User-Id: 1" | python3 -m json.tool
# → {"order_id": 1, "user_id": 1, "refunded_at": "2026-05-19T..."}
```

## 4. Attempt a duplicate refund (409)

```bash
curl -s -X POST http://localhost:8000/orders/1/refund \
  -H "X-User-Id: 1"
# → {"detail": "Order already refunded"}   HTTP 409
```

## 5. Attempt refund without authentication (401)

```bash
curl -s -X POST http://localhost:8000/orders/1/refund
# → {"detail": "Not authenticated"}   HTTP 401
```

## 6. Attempt refund for another user's order (404)

```bash
# Create a second user
curl -s -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Bob"}' | python3 -m json.tool
# → {"id": 2, "name": "Bob"}

# Try to refund user 1's order as user 2
curl -s -X POST http://localhost:8000/orders/1/refund \
  -H "X-User-Id: 2"
# → {"detail": "Order not found"}   HTTP 404
```

---

## Running the test suite

```bash
pytest tests/test_orders.py -v
```

All refund tests are prefixed `test_refund_*`.
