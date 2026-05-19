# Phase 0 Research — Order Refund Endpoint

No `NEEDS CLARIFICATION` markers were emitted in the spec; the items below
record the implementation-level decisions reached by reading the existing
codebase and constitution.

## Decision: Schema change vs. derived state

**Decision**: Store refund state on the `Order` row with a nullable
`refunded_at: datetime | None` column, and persist a separate `Refund` row
with a one-to-one relationship to `Order`.

**Rationale**:

- `Order.refunded_at IS NOT NULL` makes the "already refunded?" check a single
  cheap read and a single cheap write, matching the spec's idempotency
  requirement (FR-005).
- A dedicated `Refund` table satisfies FR-007/FR-008 ("create and persist a
  refund record … return the refund record") and leaves room for future fields
  (amount, reason) without revisiting `Order`.
- The project has no migrations (per `CLAUDE.md`: "operator will wipe `app.db`
  between runs"), so adding a nullable column and a new table is the cheapest
  schema change.

**Alternatives considered**:

- *Only add a `Refund` table; derive "refunded" via existence of a row.* Works
  but every read of an order would need a join or a separate query. The
  redundancy of `refunded_at` is small and worth the simpler lookup.
- *Boolean `is_refunded` instead of `refunded_at`.* A timestamp is strictly
  more informative at the same storage cost; rejected.

## Decision: Authentication mechanism

**Decision**: Reuse `api.deps.get_current_user` via `Depends`.

**Rationale**: `CLAUDE.md` is explicit that protected endpoints must depend
on this helper rather than re-implement it. It already returns `401` for
missing/unknown `X-User-Id`, which satisfies FR-001.

**Alternatives considered**: None — the constitution and project guardrails
both point at the existing helper.

## Decision: 30-day window boundary

**Decision**: An order is eligible while `now - order.created_at <=
timedelta(days=30)`. Boundary is inclusive.

**Rationale**: Matches the spec's Assumption ("inclusive of the full 30th
day"). `datetime.utcnow()` is what `Order.created_at` already uses (see
`src/api/models.py`), so the comparison stays in UTC and avoids any
timezone-conversion bugs.

**Alternatives considered**:

- Exclusive boundary (`< 30 days`). Rejected to match the spec.
- Switch the codebase to timezone-aware UTC. Out of scope per Principle VII
  ("Don't refactor unrelated code").

## Decision: Error responses

**Decision**: Use FastAPI's `HTTPException` with the same status-code/detail
shape already used by `get_order` in `src/api/routes/orders.py`:

| Condition | Status | Detail |
|-----------|--------|--------|
| No / unknown `X-User-Id` | 401 | from `get_current_user` |
| Order does not exist | 404 | `"order not found"` |
| Order belongs to another user | 403 | `"forbidden"` |
| Order older than 30 days | 400 | `"refund window expired"` |
| Order already refunded | 409 | `"order already refunded"` |

**Rationale**: Mirrors the existing route's idiom (Principle II + VII). 404
is reserved for "no such order" so callers cannot probe other users' order
ids — for an order that exists but belongs to another user, return 403.
`409 Conflict` is the standard code for "state would be violated by repeat".

**Alternatives considered**: A single 400-with-machine-readable-code response
for every failure. Rejected as inconsistent with the existing route, which
uses distinct status codes per failure mode.

## Decision: Response shape

**Decision**: Return a `RefundOut` Pydantic model with `id: int`,
`order_id: int`, `created_at: datetime`. Status `201 Created`.

**Rationale**: Smallest shape that satisfies FR-008 ("return the refund
record"). `201` matches the existing `create_order` route which also creates a
new persistent record.

**Alternatives considered**: Returning the order plus the refund. Rejected —
the spec asks for the refund record specifically, and a caller that wants the
order can hit `GET /orders/{id}` (which will now show it as refunded once the
spec adds the field to the response — out of scope here).
