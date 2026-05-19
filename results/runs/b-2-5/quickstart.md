# Quickstart — Order Refund Endpoint

## Run the service

```bash
uvicorn api.main:app --reload
```

## Create a user and an order (prerequisites)

```bash
# Create a user (returns {"id": 1, ...})
curl -s -X POST http://127.0.0.1:8000/users \
  -H 'content-type: application/json' \
  -d '{"email":"a@example.com","name":"A"}'

# Create an order for that user (returns {"id": 42, ...})
curl -s -X POST http://127.0.0.1:8000/orders \
  -H 'content-type: application/json' \
  -H 'x-user-id: 1' \
  -d '{"items":[{"sku":"sku-1","quantity":1,"unit_price":9.99}]}'
```

## Refund the order

```bash
curl -s -X POST http://127.0.0.1:8000/orders/42/refund \
  -H 'x-user-id: 1'
# -> 201 Created
# {"id": 7, "order_id": 42, "created_at": "2026-05-19T14:23:01"}
```

## Common failure cases

```bash
# Missing auth
curl -i -X POST http://127.0.0.1:8000/orders/42/refund
# -> 401

# Wrong user
curl -i -X POST http://127.0.0.1:8000/orders/42/refund \
  -H 'x-user-id: 2'
# -> 403

# Unknown order
curl -i -X POST http://127.0.0.1:8000/orders/99999/refund \
  -H 'x-user-id: 1'
# -> 404

# Refund twice
curl -i -X POST http://127.0.0.1:8000/orders/42/refund \
  -H 'x-user-id: 1'
# -> 409
```

## Run the tests

```bash
pytest tests/test_refunds.py -q
```
