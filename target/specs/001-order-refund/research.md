# Phase 0 — Research & Decisions

User invoked `/speckit-plan` with "Accept defaults", so each open
clarification question from the spec is resolved by the
recommended/most-sensible default already noted during `/speckit-clarify`.
No external research was required — every decision is grounded in the
existing repo conventions (CLAUDE.md) and constitution.

---

## D1. Refund record fields

- **Decision**: `Refund` row carries `id`, `order_id`, `amount` (integer
  cents, snapshotted from `Order.total` at refund time), `created_at`.
- **Rationale**: Snapshotting the amount keeps the refund record
  self-describing and auditable independently of the order row. Matches
  the existing pattern of storing money as integer cents (`Order.total`,
  `OrderItem.unit_price`). No `reason` field — the user request never
  mentioned one and the constitution forbids speculative scope creep.
- **Alternatives considered**:
  - Minimal (`id`, `order_id`, `created_at`) — rejected: loses
    auditability if the order row is later mutated.
  - Plus `reason` — rejected as speculative; not in spec.
  - Plus denormalized `user_id` — rejected; derivable via
    `refund.order.user_id`.

## D2. Order refunded-state representation

- **Decision**: Add `Order.refunded_at: Mapped[datetime | None]`, nullable,
  defaulting to NULL.
- **Rationale**: One column captures both "is refunded" (truthiness) and
  "when". Cheaper than a separate boolean + timestamp pair. SQLite + the
  project's "no migrations" rule (operator wipes `app.db` between runs)
  means schema evolution cost is zero.
- **Alternatives considered**:
  - Boolean `refunded` — rejected: loses "when" without joining `refunds`.
  - `status` enum/string — rejected: orders today have no status; adding
    one is broader than the feature.

## D3. Request body shape

- **Decision**: No request body. The endpoint takes only the path
  parameter `order_id` and the `X-User-Id` header.
- **Rationale**: Spec says full refunds only and never mentions a
  reason. Smallest surface area.

## D4. Authorization model

- **Decision**: Owner-only. The endpoint depends on `get_current_user`
  and rejects any request where `order.user_id != current_user.id` with
  HTTP 404 (so it does not disclose existence to non-owners).
- **Rationale**: Spec FR-003 mandates owner-only and explicitly forbids
  disclosing existence to non-owners. No admin role exists in the
  service today.
- **Alternatives considered**: Admin override — rejected, no admin
  role in the project.

## D5. Concurrency / idempotency

- **Decision**: Enforce "at most one refund per order" via a `UNIQUE`
  constraint on `refunds.order_id` (DB-level). In the handler, do a
  pre-check (refunded_at is NULL? no existing refund?) and rely on the
  unique constraint as the authoritative serializer. On an
  `IntegrityError` from a concurrent insert, the route catches it and
  returns the same 409-style "already refunded" response.
- **Rationale**: SQLite serializes writes at the file level so the race
  window is narrow, but the unique constraint is the correct backstop
  on any backend and is essentially free to add.
- **Alternatives considered**: SELECT ... FOR UPDATE — not portable to
  SQLite; unnecessary given the unique constraint.

## D6. HTTP status codes (error mapping)

- **Decision** (consistent with existing routes in `routes/orders.py`):
  - Missing/invalid `X-User-Id` → 401 (handled by `get_current_user`).
  - Order not found OR not owned by requester → **404** (`order not found`).
    Per FR-003, non-owners MUST NOT learn the order exists, so a unified
    404 is the safest response.
  - Order older than 30 days → **400** (`refund window expired`).
  - Order already refunded → **409** (`order already refunded`).
- **Rationale**: Aligns with existing handlers in `routes/orders.py`
  (e.g., `get_order` returns 404 on missing, 403 on non-owner — but for
  the refund route we collapse not-found and forbidden to a single 404
  to satisfy FR-003's non-disclosure rule). 409 is the standard "state
  conflict" status for the already-refunded case.

## D7. Response shape

- **Decision**: Pydantic `RefundOut { id: int, order_id: int, amount: int, created_at: str }`.
  `created_at` is serialized as ISO-8601 (`isoformat()`), departing from
  the legacy `%Y-%d-%m` format used in `OrderOut` — that legacy format
  is a buggy oddity in the existing code (day/month swapped) and the
  constitution forbids "refactoring unrelated code", so we just don't
  propagate the bug into a new endpoint.
- **Rationale**: ISO-8601 is the unambiguous default and matches typical
  Pydantic v2 datetime serialization.

## D8. Test scope

- **Decision**: One new test file `tests/test_refunds.py` covering:
  1. Happy path — eligible order, returns refund record, order is
     subsequently marked refunded.
  2. Missing `X-User-Id` → 401.
  3. Unknown `order_id` → 404.
  4. Order owned by another user → 404 (non-disclosure).
  5. Order created >30 days ago → 400.
  6. Order already refunded → 409 (second call against same order).
- **Rationale**: Constitution requires happy + ≥1 error path per new
  route; spec lists 5 distinct error branches and SC-004 requires test
  coverage of each. Six tests cover them all and keep `tests/` flat.
- **80%-coverage hook**: The refund handler is small enough that the
  six tests above will trivially exceed 80% line coverage on the
  changed files.
