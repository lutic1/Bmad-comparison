# Phase 0 Research: Percentage Discount Codes at Checkout

The Technical Context in `plan.md` has no `NEEDS CLARIFICATION` markers
— the existing stack (Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic
v2, pytest, SQLite) fully constrains the technology choices, and the
spec's Assumptions section closes the remaining product-level
ambiguities. This document records the few small design decisions made
within those constraints so reviewers can see the alternatives that
were considered.

## Decision 1 — Exact code strings

- **Decision**: `SAVE5` → 5%, `SAVE10` → 10%, `SAVE20` → 20%. Stored as
  a module-level constant `DISCOUNT_CODES: dict[str, int]` in
  `src/api/routes/orders.py`. Lookup is case-insensitive (`.upper()`
  before lookup).
- **Rationale**: The spec deferred exact strings to planning (see
  Assumptions). `SAVE{n}` is the dominant industry convention,
  immediately understandable in tests, and avoids the work of designing
  a code-issuance system that v1 is explicitly out of scope for.
- **Alternatives considered**:
  - Random opaque codes (e.g., `7K3-XQ`): better for anti-abuse, but no
    issuance/distribution flow exists yet — wasted effort for v1.
  - Configuration via env var / DB table: future-proof but violates the
    constitution's "no abstractions for a single call site" — three
    fixed codes don't justify a new table or settings module.

## Decision 2 — Where the discount is applied in the order lifecycle

- **Decision**: Add `POST /orders/{order_id}/discount` accepting a JSON
  body `{"code": "SAVE10"}`. The order is created first via the
  existing `POST /orders`; the discount endpoint mutates `subtotal`
  (set on first call from the existing `total`), `discount_code`, and
  `total` on that same order.
- **Rationale**: The existing service has no pending/confirmed split —
  an order is created in one POST. Putting the discount on a separate
  endpoint:
  - directly supports US3 (replace a previously applied code) without
    inventing a "cart" abstraction;
  - keeps the existing `POST /orders` unchanged, honouring the
    constitution's "don't refactor unrelated code in the same change";
  - reuses `get_current_user` and the existing 403/404 patterns from
    `GET /orders/{order_id}`.
- **Alternatives considered**:
  - Accept `discount_code` on `POST /orders` only: simpler, but
    can't satisfy US3 (replace) without a separate endpoint anyway.
  - New "cart"/"checkout" entity: large refactor disallowed by scope;
    spec explicitly limits scope to discount application.

## Decision 3 — Money representation and rounding

- **Decision**: Compute the discount in integer cents.
  `discount_cents = (subtotal_cents * percentage + 50) // 100`,
  `total_cents = subtotal_cents - discount_cents`. The `+ 50 // 100`
  form is integer half-up rounding for non-negative numerators (always
  true here: `subtotal_cents >= 0`, `percentage in {5, 10, 20}`).
- **Rationale**: The `orders.total` column is already integer cents
  (see `OrderItem.unit_price` and `_to_cents`). Staying in integers
  removes any IEEE-754 surprises and matches the existing data shape.
  Half-up matches the spec's edge-case note on rounding.
- **Alternatives considered**:
  - `decimal.Decimal`: correct but introduces type-mixing with the
    existing integer-cents columns for zero practical benefit at this
    scale.
  - `round()` on floats: rejected — banker's rounding semantics
    contradict the spec's "standard half-up rounding".

## Decision 4 — Schema additions on `Order`

- **Decision**: Add two nullable columns to `orders`:
  - `subtotal: Mapped[int | None]` — set the first time a discount is
    applied (snapshots the pre-discount cents total); stays `NULL` on
    orders that never had a discount, to keep existing rows valid.
  - `discount_code: Mapped[str | None]` — uppercase code string;
    `NULL` when no discount is in effect.
- **Rationale**: CLAUDE.md says the operator wipes `app.db` between
  runs and migrations aren't written — additive nullable columns are
  the cheapest safe change. Storing `subtotal` separately is necessary
  to satisfy US3 (the second `apply` must compute off the original
  subtotal, not the already-discounted total).
- **Alternatives considered**:
  - Re-derive subtotal from `OrderItem` rows on each discount call:
    works, but couples discount logic to item iteration and makes the
    "snapshot at first apply" semantics implicit.
  - A separate `order_discounts` table: over-engineered for one active
    code per order.

## Decision 5 — Test approach

- **Decision**: New file `tests/test_discounts.py` using the existing
  `client` fixture. Cover: each of the three percentages on a known
  subtotal (FR-002, FR-003, SC-001), case-insensitive lookup (FR-006),
  invalid code → 400 (FR-005, SC-002), empty code → 400 (FR-005),
  replace-existing-code (FR-007, SC-003), order owned by another user
  → 403, unknown order → 404, subtotal-0 edge case from spec.
- **Rationale**: Mirrors the structure of `tests/test_orders.py`; one
  behaviour per test (per CLAUDE.md). FR-009 explicitly requires these.
- **Alternatives considered**:
  - Unit-testing a pure discount helper without HTTP: less coverage of
    the auth/ownership wiring that the constitution's "every new route
    ships with happy-path and at least one error-path test" cares
    about. Stick with HTTP-level tests.
