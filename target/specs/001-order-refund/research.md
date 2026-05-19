# Phase 0 Research: Order Refund

No `NEEDS CLARIFICATION` markers were left in the Technical Context. The
spec's Assumptions section already resolved the ambiguous points. The
research below records the few choices the plan still depends on, with
rationale and alternatives, so the design phase has a stable footing.

## Decision: Where the refund endpoint lives

- **Decision**: Add the handler to the existing `src/api/routes/orders.py`
  on the existing `router = APIRouter(prefix="/orders", tags=["orders"])`.
- **Rationale**: The path is `POST /orders/{order_id}/refund` — keyed by
  an order. `GET /orders/{order_id}` already lives here. Splitting refunds
  into a separate file would create two routers for the same resource and
  contradict the project guideline against introducing abstractions for a
  single call site.
- **Alternatives considered**:
  - Separate `routes/refunds.py` with its own router — rejected: extra
    file, extra import in `main.py`, no isolation benefit for one route.

## Decision: How an order is marked as refunded

- **Decision**: Add a nullable `refunded_at: Mapped[datetime | None]`
  column to the existing `Order` model. `NULL` means "not refunded";
  a timestamp means "refunded at that time".
- **Rationale**: FR-007 requires the refunded state to be observable on
  subsequent reads of the order; storing it directly on `Order` makes
  reads a single-row lookup with no join. CLAUDE.md states the operator
  wipes `app.db` between runs, so no migration is required. A single
  column is the simplest representation that satisfies the requirement.
- **Alternatives considered**:
  - Derive "is refunded" purely from the existence of a `Refund` row —
    rejected: every read of an `Order` would have to query `refunds`
    too, and ad-hoc consumers (DB inspection, future endpoints) would
    have to know the join. The column makes the state self-contained.
  - Add a boolean `is_refunded` column — rejected: a timestamp carries
    strictly more information for the same storage cost and matches the
    existing `created_at` pattern on the same table.

## Decision: Refund record persistence

- **Decision**: New `Refund` model in `src/api/models.py` with columns
  `id` (PK), `order_id` (FK to `orders.id`, **unique**), `amount` (int
  cents), `created_at` (UTC datetime, defaults to `datetime.utcnow`).
- **Rationale**: One refund per order (spec: "An order may be refunded
  at most once. Partial refunds are out of scope."). A unique constraint
  on `order_id` is the database-level enforcement that backs the
  application-level "already refunded → reject" rule. `amount` mirrors
  the existing `Order.total` representation (integer cents) so the
  refund record is comparable to the order it refunds.
- **Alternatives considered**:
  - Skip the dedicated table and just stamp `refunded_at` on the order —
    rejected: FR-008 requires *returning* a refund record with id, order
    reference, and timestamp; that record needs a primary key.
  - Allow multiple refunds per order — rejected: out of scope per spec
    assumptions.

## Decision: Refund amount

- **Decision**: The refund amount equals the order's current `total` (in
  cents). It is captured on the `Refund` row at creation time.
- **Rationale**: The spec is silent on partial refunds and explicitly
  excludes them. Snapshotting the order's total onto the refund row
  avoids ambiguity if `Order.total` is ever recomputed later.
- **Alternatives considered**:
  - Accept an `amount` in the request body — rejected: not in scope,
    invites partial-refund semantics the spec excluded.

## Decision: 30-day window evaluation

- **Decision**: Compare `datetime.utcnow() - order.created_at` against
  `timedelta(days=30)`. The boundary is inclusive of day 30
  (i.e. allowed iff `delta <= timedelta(days=30)`), matching the edge
  case noted in the spec.
- **Rationale**: `Order.created_at` is already populated via
  `datetime.utcnow` (see `models.py`), so using the same clock keeps
  the comparison consistent. Stdlib `datetime` / `timedelta` only — no
  new dependency.
- **Alternatives considered**:
  - Exclusive boundary (`< 30 days`) — rejected: spec explicitly states
    "inclusive of day 30".

## Decision: Status codes for rejection paths

- **Decision**:
  - Missing/invalid `X-User-Id` → 401 (reuses `get_current_user`'s
    existing behaviour).
  - Order does not exist → 404.
  - Order exists but belongs to another user → 404 (not 403). The spec
    requires that we MUST NOT reveal whether such an order exists.
  - Order is older than 30 days → 400 with a clear message.
  - Order is already refunded → 409 Conflict.
- **Rationale**: Existing `GET /orders/{order_id}` returns 403 for the
  cross-user case, which leaks "this id exists". The spec for refunds
  explicitly forbids that disclosure, so we return 404 instead. This is
  a feature-local difference, not a refactor of the existing GET. 409
  for already-refunded matches typical REST conventions for a
  conflicting-state precondition that the client could have anticipated.
- **Alternatives considered**:
  - 403 for cross-user — rejected, violates the no-disclosure rule.
  - 422 for outside-window — rejected: 422 is FastAPI's body-validation
    code; 400 reads more clearly for a business-rule violation that
    isn't a schema problem.
  - 400 for already-refunded — rejected: 409 better signals "the
    resource is in a state incompatible with the request".

## Decision: Request and response shapes

- **Decision**:
  - Request body: empty (no fields). The endpoint takes the path
    parameter `order_id` and the `X-User-Id` header; that is sufficient.
  - Response body (`RefundOut`): `{ id: int, order_id: int, amount: int,
    created_at: str }` with `created_at` ISO 8601, matching Pydantic v2
    defaults. (Note: the existing `OrderOut.created_at` uses a custom
    `%Y-%d-%m` format — see CLAUDE.md guidance not to refactor unrelated
    code; we leave that alone and use ISO 8601 here, where it is new.)
- **Rationale**: Minimal surface area, no fields the caller could
  manipulate to invite partial-refund semantics.
- **Alternatives considered**:
  - Mirror the existing `%Y-%d-%m` format for consistency — rejected: it
    is an obvious bug (day and month swapped) but fixing it is out of
    scope. New code emits ISO 8601, which is the FastAPI/Pydantic
    default.

## Decision: Test layout

- **Decision**: One new file `tests/test_refunds.py`, mirroring the
  one-resource-per-file pattern of `test_orders.py` and `test_users.py`.
- **Rationale**: Keeps the test suite navigable. Reuses the existing
  `client` fixture from `tests/conftest.py` without modification.
- **Alternatives considered**:
  - Append refund tests to `test_orders.py` — rejected: it would grow a
    file already covering create/get and obscure the per-resource
    organisation.

## Output

All Technical Context items resolved. Ready for Phase 1.
