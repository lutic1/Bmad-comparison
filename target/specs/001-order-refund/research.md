# Phase 0 Research: Order Refund

The spec left several decision points open (no `[NEEDS CLARIFICATION]`
markers, but several "implied but not stated" requirements were surfaced
in the clarify pass). The user asked planning to accept default
recommendations. The defaults are recorded here so downstream
phases reference a single source of truth.

## Decision 1 — Refund record contents

**Decision**: Refund record stores `id`, `order_id`, `amount` (integer
cents copied from `Order.total` at refund time), and `created_at` (UTC
timestamp).

**Rationale**: An orders/payments system needs the refund record to
stand on its own — accounting and customer-support consumers should not
have to re-derive the amount by joining back to the order, which could
also be mutated independently later. Cents (int) matches the existing
`Order.total` representation in `src/api/models.py`.

**Alternatives considered**:
- Marker only (id, order_id, timestamp). Rejected: makes the record
  useless for downstream reconciliation.
- Add a free-text `reason`. Rejected for v1: not in the user request,
  and can be added later without breaking the schema.

## Decision 2 — Marking an order as refunded

**Decision**: Add `Order.refunded_at: Mapped[datetime | None]` (nullable
column, default `None`). Presence of a value means "refunded"; absence
means "not refunded". The column is set in the same DB transaction that
inserts the `Refund` row.

**Rationale**: The spec explicitly allows adding a field ("mark the
order as refunded (add a field if needed)"). A nullable timestamp gives
both the boolean state and the "when" without introducing a separate
boolean. Matches the existing `created_at` style on `Order`. Project
convention (per `CLAUDE.md`) is that the operator wipes `app.db`
between runs, so no migration is needed.

**Alternatives considered**:
- `refunded: Mapped[bool]`. Rejected: loses the timestamp without
  saving any space, and the `Refund` table is the source of truth for
  "when" anyway, so duplication is acceptable for read convenience.
- Derive refunded state via `EXISTS` against the `refunds` table on
  every read. Rejected: slower and forces every order read site to
  know about the refunds table.

## Decision 3 — Response on "already refunded"

**Decision**: Return HTTP 409 Conflict with detail `"order already
refunded"`. Distinct from 404 (not found / not yours) and 422 (window
expired).

**Rationale**: FR-008 requires the four failure modes to be
distinguishable. 409 is the conventional HTTP status for a state
conflict on an existing resource. The owner of the order already knows
the order exists (they made it), so revealing the "already refunded"
state to them does not leak information.

**Alternatives considered**:
- Treat duplicate refund as idempotent success (return the existing
  refund record). Rejected: the spec explicitly says "prevent the same
  order from being refunded more than once" and lists "already
  refunded" as a distinct failure mode — that is a reject, not a
  silent success.
- Return 404 to hide the order's refund state. Rejected: the caller is
  the owner; nothing to hide.

## Decision 4 — Response on "not your order" vs "order not found"

**Decision**: Both return HTTP 404 Not Found with detail `"order not
found"` — identical responses, per the spec's Assumptions section.

**Rationale**: The spec explicitly calls out this assumption to avoid
leaking the existence of other users' orders. Matches the convention
used elsewhere in the project (the existing `GET /orders/{order_id}`
returns 403 for not-owner, which is a known information leak; we do
**not** propagate that leak into the new endpoint).

**Alternatives considered**:
- Reuse the existing 403 for not-owner. Rejected: violates the spec's
  explicit assumption.
- Refactor the existing GET to also return 404 for not-owner.
  Rejected: out of scope per constitution ("Don't refactor unrelated
  code in the same change").

## Decision 5 — Response on "window expired"

**Decision**: Return HTTP 422 Unprocessable Entity with detail `"refund
window expired"`.

**Rationale**: The request is well-formed and the caller is authorized,
but a semantic precondition fails. 422 is the conventional status for
this in FastAPI/Pydantic-style services. Distinct from 409 (state
conflict) and 404 (resource).

**Alternatives considered**:
- 400 Bad Request. Rejected: the request itself is valid; the order's
  age is what's wrong.

## Decision 6 — Refund-window precision

**Decision**: Reject when `(now_utc - order.created_at) > timedelta(days=30)`.
Boundary is inclusive of the 30th day (i.e., an order exactly 30 days
old at the second is still refundable), matching the spec's stated
assumption.

**Rationale**: Project uses naive UTC `datetime.utcnow()` throughout
(`src/api/models.py:18`, `src/api/models.py:32`). Using
`datetime.utcnow()` here keeps the comparison consistent. `timedelta`
gives sub-second precision, which is the simplest interpretation of
"30 days".

**Alternatives considered**:
- Calendar-day arithmetic with timezone awareness. Rejected: project
  has no timezone handling and stores naive UTC.

## Decision 7 — Request body

**Decision**: No request body required. The endpoint takes `order_id`
in the path, the user from `X-User-Id`, and that is sufficient to
process the refund.

**Rationale**: User request does not require any body fields. Spec edge
case mentioning "empty or malformed body" is satisfied because FastAPI
will accept an empty body for a route that declares no body model.

**Alternatives considered**:
- Require an empty JSON object `{}`. Rejected: needless friction.
- Accept an optional reason. Deferred — see Decision 1.

## Decision 8 — Concurrency / duplicate prevention

**Decision**: The handler performs an existence check on
`Order.refunded_at` inside the same transaction as the insert + update,
then commits once. SQLite's per-connection serial write semantics in
the test fixture and single-writer prod config make a race window
benign; if two requests interleave, the second commit will simply see
`refunded_at` set after re-read. We do **not** add explicit row locking.

**Rationale**: The project uses SQLite and has no concurrency story
documented; adding `SELECT ... FOR UPDATE` would be both a no-op on
SQLite and out of step with the rest of the codebase. The constraint
is enforced by the application check + single transaction, which is
sufficient for this stack.

**Alternatives considered**:
- A `UNIQUE` constraint on `refunds.order_id`. Considered but not
  adopted: would also work, but the `Order.refunded_at` check is the
  primary guard and the unique constraint would add a second
  enforcement site without changing behavior visible to the caller.
  Easy to add later if duplicates ever appear.

## Output

All decisions resolved. No remaining `NEEDS CLARIFICATION`. Ready for
Phase 1.
