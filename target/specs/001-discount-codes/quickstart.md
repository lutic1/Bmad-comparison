# Quickstart: Percentage Discount Codes at Checkout

Quick end-to-end demo of the new endpoint against a freshly-wiped
`app.db`. Assumes the service is run from the repository root.

## 1. Run the service

```bash
rm -f app.db                  # schema is recreated from Base.metadata at startup
uvicorn api.main:app --reload
```

## 2. Create a user

```bash
curl -s -X POST http://localhost:8000/users \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","name":"Demo"}'
# → {"id":1,"email":"demo@example.com","name":"Demo", ...}
```

## 3. Create an order with a $100.00 subtotal

```bash
curl -s -X POST http://localhost:8000/orders \
  -H 'X-User-Id: 1' \
  -H 'Content-Type: application/json' \
  -d '{"items":[{"sku":"WIDGET","quantity":2,"unit_price":50.00}]}'
# → {"id":1,"total":10000, ...}            (cents)
```

## 4. Apply a 10% discount

```bash
curl -s -X POST http://localhost:8000/orders/1/discount \
  -H 'X-User-Id: 1' \
  -H 'Content-Type: application/json' \
  -d '{"code":"SAVE10"}'
# → {"id":1,"subtotal":10000,"discount_code":"SAVE10","total":9000, ...}
```

## 5. Replace it with 20%

```bash
curl -s -X POST http://localhost:8000/orders/1/discount \
  -H 'X-User-Id: 1' \
  -H 'Content-Type: application/json' \
  -d '{"code":"save20"}'   # case-insensitive
# → {"id":1,"subtotal":10000,"discount_code":"SAVE20","total":8000, ...}
```

Note that `total` is 8000 (20% off the original 10000), **not** 7200
(20% off the already-discounted 9000). This is the US3 / SC-003
guarantee.

## 6. Reject an invalid code

```bash
curl -s -X POST http://localhost:8000/orders/1/discount \
  -H 'X-User-Id: 1' \
  -H 'Content-Type: application/json' \
  -d '{"code":"NOPE"}'
# → 400 {"detail":"invalid discount code"}
```

The order's `total` is unchanged (still 8000).

## 7. Run the tests

```bash
pytest tests/test_discounts.py -q
```

All scenarios from spec.md (FR-001..FR-009, SC-001..SC-004) are
covered there.
