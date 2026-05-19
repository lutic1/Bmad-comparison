# Phase 0 Research — Order Refund

The spec left a handful of items implied-but-not-stated. The clarify
step was skipped, so this document records the defaults chosen and why.
No `NEEDS CLARIFICATION` markers remain.

## Decision 1 — Refund record fields

- **Decision**: `Refund(id, order_id, amount, created_at)`. `order_id`
  carries a UNIQUE constraint.
- **Rationale**: Self-contained historical record. Storing `amount` on
  the refund (rather than deriving it from the order at read time)
  keeps the refund stable if order data ever changes. Minimal — matches
  CLAUDE.md's "no over-engineering" and "stdlib first" guidance. The
  UNIQUE constraint on `order_id` makes "at most one refund per order"
  a database-level invariant, which is the simplest way to satisfy
  FR-007 / SC-003 under any concurrency.
- **Alternatives considered**:
  - Derive amount from `Order.total` at read time — rejected: refund
    record becomes coupled to the order's mutable state.
  - Add a `reason` text field — rejected: not requested; speculative.
  - Add a `status` (pending/completed) field — rejected: refunds in
    this feature are synchronous internal state changes; no lifecycle.

## Decision 2 — Marking the order as refunded

- **Decision**: Add a nullable `refunded_at: datetime | None` column to
  `Order`. `None` means not refunded; a timestamp means refunded.
- **Rationale**: Single column captures both the boolean state and the
  moment it happened (useful for the response and for "already
  refunded" rejection without joining the `refunds` table). Aligns
  with the existing `created_at` pattern on `Order`.
- **Alternatives considered**:
  - Boolean `is_refunded` — rejected: loses the timestamp and is
    redundant with the refund row's `created_at`.
  - Compute refunded state via join on `refunds` — rejected: extra
    query for every order read; not warranted.

## Decision 3 — Ownership disclosure (404 vs 403)

- **Decision**: Mirror the existing pattern in `api/routes/orders.py`:
  return `404` when the order does not exist, `403` when it exists but
  belongs to another user.
- **Rationale**: Consistency with the only other place in the codebase
  that handles the same situation (`get_order`). Adopting a different
  policy here would be an unrelated refactor.
- **Alternatives considered**:
  - Collapse both to `404` to avoid leaking existence — rejected for
    this change: would diverge from the rest of the API for marginal
    benefit and would constitute an unrelated policy change.

## Decision 4 — HTTP status codes for the other rejection paths

- **Decision**:
  - Missing/invalid `X-User-Id` → `401` (already handled by
    `get_current_user`).
  - Order older than 30 days → `400` with detail
    `"refund window expired"`.
  - Order already refunded → `409` with detail
    `"order already refunded"`.
  - Order not found / not owned → `404` / `403` per Decision 3.
- **Rationale**: `409 Conflict` matches "state precludes the action";
  `400` matches "request violates a business rule on the resource".
- **Alternatives considered**:
  - `422` for the 30-day window — rejected: the request body itself is
    valid; the rule is on the resource state.

## Decision 5 — "Within 30 days" boundary

- **Decision**: Inclusive of 30 days. Computed as
  `now - order.created_at <= timedelta(days=30)` using
  `datetime.utcnow()` (matching the project's existing convention in
  `models.py`).
- **Rationale**: Spec edge cases already state "exactly 30 days … is
  considered within the window".
- **Alternatives considered**:
  - Exclusive (`< 30 days`) — rejected: contradicts the spec.

## Decision 6 — Refund amount source

- **Decision**: Refund amount = `order.total` (integer cents), copied
  onto the refund row at creation time.
- **Rationale**: Spec assumption explicitly states full-order refunds
  only; partial refunds are out of scope. Using the existing cents
  representation keeps the data model uniform.
- **Alternatives considered**:
  - Accept an `amount` in the request body — rejected: would imply
    partial refunds, which are out of scope.

## Decision 7 — Where the route lives

- **Decision**: New module `src/api/routes/refunds.py` that defines an
  `APIRouter(prefix="/orders", tags=["refunds"])` and is registered in
  `src/api/main.py`. The existing `routes/orders.py` is untouched.
- **Rationale**: Keeps the diff scoped (no unrelated edits to
  `orders.py`) and matches FastAPI's normal pattern of one router
  module per resource concern.
- **Alternatives considered**:
  - Add the endpoint to `routes/orders.py` — rejected: would mix
    refund concerns into the orders module and broaden the diff for
    no benefit.

## Decision 8 — Testing approach

- **Decision**: One new file `tests/test_refunds.py` using the existing
  `client` fixture from `conftest.py`. One test per behaviour, named
  `it_should_*` style consistent with the project's existing tests.
  Order ages older than 30 days are produced by directly setting
  `order.created_at` on the seeded row (not by sleeping).
- **Rationale**: Matches the project's stated testing conventions
  (one behaviour per test, in-memory SQLite per test, no time-based
  flakiness). No new fixtures or dependencies needed.
- **Alternatives considered**:
  - Freezing time with a library (`freezegun`) — rejected: introduces
    a new dependency for a problem solvable by writing a timestamp.
