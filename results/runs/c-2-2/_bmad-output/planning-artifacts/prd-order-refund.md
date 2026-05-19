# PRD: Order Refund Endpoint

**Status:** Draft  
**Author:** John (PM)  
**Date:** 2026-05-19  
**Stack context:** FastAPI · SQLAlchemy 2.x (declarative `Mapped[...]`) · SQLite · Pydantic v2 · pytest

---

## 1. Problem Statement

Users have no programmatic way to request a refund on an order they placed. The service currently has no refund concept — no status flag on `Order`, no refund record, no endpoint. A user who needs a refund has no self-serve path.

---

## 2. Goals

1. **Self-serve refund initiation** — authenticated users can mark one of their own orders as refunded via a single HTTP call.
2. **Time-bounded eligibility** — refunds are only accepted within 30 calendar days of order creation, enforcing a clear policy window without manual review.
3. **Idempotency-safe state** — the order carries a durable `refunded` flag so the system (and future integrations) can always query refund status.
4. **Consistent response shape** — the endpoint returns a structured refund record so callers have a canonical record of what was refunded and when.
5. **Full test coverage** — every acceptance criterion below has a corresponding pytest test using the existing `client` fixture.

---

## 3. Non-Goals

- **Payment gateway integration.** No money is moved. The endpoint records intent only.
- **Partial refunds.** The full order total is refunded atomically; line-item granularity is out of scope.
- **Admin override path.** No back-office endpoint to bypass the 30-day window.
- **Refund cancellation / reversal.** Once marked refunded, the state is final for this iteration.
- **Email / webhook notification.** No side-effects beyond the database write.
- **Audit log / history table.** A single `refunded_at` timestamp on `Order` is sufficient; a separate `Refund` table is not required unless AC review says otherwise (see Open Questions).
- **Migrations.** Per `CLAUDE.md`, schema changes are handled by wiping `app.db`; no Alembic migration needed.
- **Rate limiting / abuse prevention.** Already handled by existing middleware; no new policy needed.

---

## 4. User Story

> As an authenticated user, I want to POST to `/orders/{order_id}/refund` so that my order is marked refunded and I receive a confirmation record, provided the order is mine and was placed within the last 30 days.

---

## 5. Acceptance Criteria

### 5.1 Authentication
| ID | Criterion |
|----|-----------|
| AC-1 | Request without `X-User-Id` header → `401 Unauthorized` |
| AC-2 | Request with `X-User-Id` for a non-existent user → `401 Unauthorized` |

### 5.2 Authorization & Ownership
| ID | Criterion |
|----|-----------|
| AC-3 | Order does not exist → `404 Not Found` |
| AC-4 | Order exists but belongs to a different user → `403 Forbidden` |

### 5.3 Refund Eligibility
| ID | Criterion |
|----|-----------|
| AC-5 | Order `created_at` is within 30 days of the request timestamp → refund succeeds |
| AC-6 | Order `created_at` is exactly 30 days ago (boundary) → refund succeeds |
| AC-7 | Order `created_at` is more than 30 days ago → `422 Unprocessable Entity` with a descriptive error detail |
| AC-8 | Order already marked as refunded → `409 Conflict` (idempotency: second call is rejected, not silently accepted) |

### 5.4 State Mutation
| ID | Criterion |
|----|-----------|
| AC-9 | On success, `Order.refunded` is set to `True` and `Order.refunded_at` is set to the current UTC timestamp |
| AC-10 | The mutation is persisted; a subsequent `GET /orders/{order_id}` reflects the refunded state |

### 5.5 Response Shape
| ID | Criterion |
|----|-----------|
| AC-11 | `201 Created` on success |
| AC-12 | Response body contains: `order_id` (int), `refunded_at` (ISO-8601 string), `total` (int, cents) |

### 5.6 Tests
| ID | Criterion |
|----|-----------|
| AC-13 | A dedicated test file covers every AC above with one behaviour per test |
| AC-14 | All existing tests remain green |

---

## 6. Proposed Response Schema

```json
{
  "order_id": 42,
  "refunded_at": "2026-05-19T14:32:00",
  "total": 1998
}
```

`total` echoes the order's original amount (in cents) so the caller knows what was refunded without a second GET.

---

## 7. Data Model Changes

**`Order` table — two new columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `refunded` | `Boolean` | No | `False` |
| `refunded_at` | `DateTime` | Yes | `NULL` |

No separate `Refund` table is required for v1. The `Order` row is the refund record.

---

## 8. Boundary & Edge-Case Notes

- **30-day calculation:** `datetime.utcnow() - order.created_at > timedelta(days=30)`. The boundary (exactly 30 days) is inclusive — refund is allowed.
- **Timezone:** Both `Order.created_at` and the comparison timestamp use UTC (consistent with existing `datetime.utcnow()` default in the model).
- **Cents integrity:** `total` in the response is the stored integer cents value — no conversion needed.

---

## 9. Open Questions

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| OQ-1 | Should `GET /orders/{order_id}` response include `refunded` and `refunded_at` fields after this change? If yes, `OrderOut` schema must be updated. | Minor API surface expansion; affects callers of the existing GET | Luisticas |
| OQ-2 | Is `409 Conflict` the right status for "already refunded", or should it be idempotent (`200` returning the existing refund record)? | Affects client retry logic | Luisticas |
| OQ-3 | Is the 30-day window calendar days or business days? Current assumption: calendar days. | Business logic correctness | Luisticas |
| OQ-4 | Should `refunded` orders be blocked from further state changes (e.g., if an "cancel order" endpoint is added later)? | Future-proofing; out of scope for v1 but worth noting | Architect |

---

## 10. Success Metrics

- All 14 acceptance criteria pass in CI (`pytest` green, no regressions).
- No new third-party dependencies introduced.
- Endpoint added in `src/api/routes/orders.py` following existing route patterns.
