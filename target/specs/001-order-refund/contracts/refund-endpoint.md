# Contract: POST /orders/{order_id}/refund

**Feature**: `001-order-refund`
**Date**: 2026-05-18

## Endpoint

```
POST /orders/{order_id}/refund
```

## Request

### Path Parameters

| Parameter  | Type | Required | Description         |
|------------|------|----------|---------------------|
| order_id   | int  | yes      | ID of the order to refund |

### Headers

| Header      | Type | Required | Description                        |
|-------------|------|----------|------------------------------------|
| X-User-Id   | int  | yes      | ID of the authenticated user       |

### Body

None.

## Responses

### 200 OK — Refund processed

```json
{
  "order_id": 42,
  "refunded_at": "2026-05-18T14:30:00",
  "amount": 4999
}
```

| Field        | Type     | Description                              |
|--------------|----------|------------------------------------------|
| order_id     | int      | ID of the refunded order                 |
| refunded_at  | datetime | UTC ISO-8601 timestamp of refund         |
| amount       | int      | Refunded amount in cents                 |

### 401 Unauthorized — Missing or invalid identity

```json
{"detail": "missing X-User-Id header"}
```
```json
{"detail": "unknown user"}
```

### 403 Forbidden — Order belongs to a different user

```json
{"detail": "forbidden"}
```

### 404 Not Found — Order does not exist

```json
{"detail": "order not found"}
```

### 422 Unprocessable Entity — Business rule violation

```json
{"detail": "refund window expired"}
```
```json
{"detail": "order already refunded"}
```

## Validation Order

1. Authentication (401 if missing/invalid)
2. Order existence (404 if not found)
3. Ownership (403 if wrong user)
4. Not already refunded (422)
5. Within 30-day window (422)

## Notes

- The 30-day window is inclusive: an order exactly 30 days old is eligible.
- `amount` is always equal to `order.total` (in cents). Partial refunds are not supported.
- The operation is idempotent in the sense that a second call after a successful refund always returns 422 — the refunded state is permanent.
