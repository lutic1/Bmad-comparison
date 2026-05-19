# PRD: Order Refund Endpoint

**Status:** Draft  
**Author:** John (PM)  
**Date:** 2026-05-19  
**Stack context:** FastAPI + SQLAlchemy 2.x (SQLite), Pydantic v2, pytest. Auth via `X-User-Id` header (`api.deps.get_current_user`). Monetary values stored as integer cents.

---

## Problem Statement

Users have no self-service way to reverse an order. There is currently no refund concept in the system — no status field, no refund record, no enforcement of refund eligibility rules. Any refund handling would have to be done out-of-band or by manually editing the database.

---

## Goals

1. Expose a `POST /orders/{order_id}/refund` endpoint that marks an order as refunded and returns a refund record.
2. Enforce ownership: only the authenticated user who placed the order may refund it.
3. Enforce a 30-day refund window measured from `Order.created_at`.
4. Prevent double-refunds: an already-refunded order must be rejected.
5. Ship with full pytest coverage: happy path, all error branches, edge cases on the 30-day boundary.

---

## Non-Goals

- No payment gateway integration, no actual money movement.
- No admin override / force-refund capability.
- No partial refunds (refund of specific items or amounts).
- No refund cancellation or reversal.
- No async processing, queuing, or webhook notifications.
- No database migrations — schema is created from `Base.metadata`; operator wipes `app.db` between runs.
- No changes to `pyproject.toml` dependencies (stdlib + existing stack only).

---

## Functional Requirements

### FR-1 Authentication
The endpoint MUST depend on `api.deps.get_current_user`. Missing or unknown `X-User-Id` → `401`.

### FR-2 Order Existence
If `order_id` does not exist in the database → `404 order not found`.

### FR-3 Ownership
If the order belongs to a different user → `403 forbidden`.

### FR-4 Idempotency / Double-Refund Guard
If the order is already refunded → `409 order already refunded`.

### FR-5 30-Day Window
If `utcnow() - order.created_at > 30 days` → `422 refund window has expired`.  
Orders created exactly 30 days ago (to the second) are still eligible.

### FR-6 State Mutation
On success, persist `Order.refunded = True` and `Order.refunded_at = utcnow()` to the database.

### FR-7 Response Shape
HTTP `201` with a JSON body representing the refund record:

```json
{
  "order_id": 7,
  "refunded_at": "2026-05-19T14:32:00",
  "total_refunded": 4999
}
```

`total_refunded` is the order's `total` in cents at the time of refund. ISO-8601 datetime string for `refunded_at`.

---

## Schema Changes

Add two columns to the `orders` table (no migration needed — schema recreated at startup):

| Column | Type | Nullable | Default |
|---|---|---|---|
| `refunded` | `Boolean` | No | `False` |
| `refunded_at` | `DateTime` | Yes | `None` |

No new tables required.

---

## Acceptance Criteria

| # | Scenario | Expected |
|---|---|---|
| AC-1 | Valid request, order within 30 days, belongs to user | `201` + refund record JSON |
| AC-2 | Missing `X-User-Id` header | `401` |
| AC-3 | Unknown `X-User-Id` | `401` |
| AC-4 | `order_id` not in DB | `404` |
| AC-5 | Order belongs to a different user | `403` |
| AC-6 | Order already refunded | `409` |
| AC-7 | Order created 31 days ago | `422` |
| AC-8 | Order created exactly 30 days ago | `201` (still eligible) |
| AC-9 | `refunded` flag is persisted; re-fetching via `GET /orders/{id}` reflects the state | Pass |
| AC-10 | `pytest` suite passes with no failures after the change | Pass |

---

## Open Questions

| # | Question | Owner | Priority |
|---|---|---|---|
| OQ-1 | Should `GET /orders/{order_id}` response expose `refunded` and `refunded_at` fields? The current `OrderOut` schema omits them. Exposing them is a non-breaking additive change. | Architect / Dev | Low |
| OQ-2 | Is UTC the agreed timezone for all datetime operations? `Order.created_at` uses `datetime.utcnow()` but Python 3.12 deprecated it in favour of timezone-aware datetimes. Should this endpoint align with existing (naive UTC) or upgrade? | Dev | Medium |
| OQ-3 | The 30-day window: is it calendar days (midnight boundaries) or rolling 720 hours from `created_at`? Spec says "30 days of order creation" — this PRD interprets it as 30 × 24 h from `created_at`. Confirm. | PM / Stakeholder | High |
| OQ-4 | Error priority when multiple conditions fail simultaneously (e.g., order exists, belongs to user, is already refunded AND is outside 30 days): which error wins? This PRD recommends: ownership first, then double-refund, then window expiry. | Dev | Low |

---

## Out-of-Scope (Explicitly Deferred)

- Refund audit log / history endpoint
- Webhook / event emission on refund
- Admin endpoints
- Partial refunds

