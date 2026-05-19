# Quickstart: Order Refund

## Prerequisites

A running instance of the service with a user and a recent order already created.

## 1. Create a user

```bash
curl -s -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "name": "Alice"}' | python3 -m json.tool
```

Note the returned `id` (e.g., `1`).

## 2. Create an order

```bash
curl -s -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{
    "items": [
      {"sku": "WIDGET-001", "quantity": 2, "unit_price": 24.99}
    ]
  }' | python3 -m json.tool
```

Note the returned `id` (e.g., `7`).

## 3. Request a refund

```bash
curl -s -X POST http://localhost:8000/orders/7/refund \
  -H "X-User-Id: 1" | python3 -m json.tool
```

Expected response (200):

```json
{
  "order_id": 7,
  "refunded_at": "2026-05-18T14:30:00",
  "amount": 4998
}
```

## Error cases

**No auth header → 401**:
```bash
curl -s -X POST http://localhost:8000/orders/7/refund
# {"detail":"missing X-User-Id header"}
```

**Wrong user → 403**:
```bash
curl -s -X POST http://localhost:8000/orders/7/refund -H "X-User-Id: 99"
# {"detail":"forbidden"}
```

**Order not found → 404**:
```bash
curl -s -X POST http://localhost:8000/orders/9999/refund -H "X-User-Id: 1"
# {"detail":"order not found"}
```

**Already refunded → 422**:
```bash
curl -s -X POST http://localhost:8000/orders/7/refund -H "X-User-Id: 1"
# {"detail":"order already refunded"}
```

**Window expired → 422** (order older than 30 days):
```bash
# {"detail":"refund window expired"}
```
