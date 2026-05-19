# Contract: POST /orders/{order_id}/refund

**Date**: 2026-05-19
**Feature**: [spec.md](../spec.md)

---

## Endpoint

```
POST /orders/{order_id}/refund
```

---

## Request

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `order_id` | integer | Yes | ID of the order to refund |

### Headers

| Header | Type | Required | Description |
|--------|------|----------|-------------|
| `X-User-Id` | integer | Yes | ID of the authenticated user |

### Body

None.

---

## Responses

### 200 OK — Refund processed

```json
{
  "order_id": 42,
  "user_id": 7,
  "refunded_at": "2026-05-19T14:30:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | integer | ID of the refunded order |
| `user_id` | integer | ID of the user who requested the refund |
| `refunded_at` | string (ISO 8601 datetime) | UTC timestamp of the refund |

### 401 Unauthorized — Missing or invalid authentication

```json
{"detail": "Not authenticated"}
```

Returned when `X-User-Id` header is absent or references a non-existent user.

### 404 Not Found — Order not found or not owned by caller

```json
{"detail": "Order not found"}
```

Returned when the order does not exist **or** exists but belongs to a different user. The response is identical in both cases to avoid disclosing order existence.

### 400 Bad Request — Refund window expired

```json
{"detail": "Refund window expired"}
```

Returned when the order was created more than 30 days before the request (strictly: `now - created_at > timedelta(days=30)`).

### 409 Conflict — Order already refunded

```json
{"detail": "Order already refunded"}
```

Returned when `order.refunded` is already `True`.

---

## Behaviour Notes

- All error conditions are checked in this order: authentication → existence/ownership → already-refunded → window.
- A successful call is idempotent in effect (order remains refunded) but returns 409 on repeat calls — callers must handle 409 as a success-equivalent if needed.
- No request body is accepted; sending one has no effect (FastAPI ignores it).
