# Research: Checkout Discount Code

## Technical Decisions

### Decision 1: No New Dependencies Required
- **Decision**: Implement entirely with the existing stack (FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest).
- **Rationale**: The feature requires a DB lookup, arithmetic, and two HTTP endpoints — all covered by existing libraries. Adding a dependency for percentage math or coupon validation would violate constitution principle V.
- **Alternatives considered**: None applicable; stdlib `round()` is sufficient for cent arithmetic.

### Decision 2: Monetary Arithmetic — Integer Cents
- **Decision**: Discount amounts are computed and stored as integer cents, consistent with the project's existing pattern (`total`, `unit_price` columns).
- **Rationale**: The codebase already uses `int(round(dollars * 100))` for all monetary values. Diverging from this would introduce inconsistency and float-precision bugs.
- **Formula**: `discount_cents = round(order.total * percent / 100)` where `order.total` is already in cents.

### Decision 3: DiscountCode Table Seeded at Startup
- **Decision**: Pre-configured discount codes are stored in a `discount_codes` DB table, seeded idempotently during the FastAPI `lifespan` startup hook.
- **Rationale**: The project has no migration system and no admin UI. Seeding in `lifespan` (already used for `Base.metadata.create_all`) is the established pattern for one-time setup. Codes can be added by re-seeding.
- **Alternatives considered**:
  - Hard-coded list in route logic — rejected; not stored/queryable, no extensibility.
  - Admin CRUD endpoints — out of scope per spec.

### Decision 4: Order-Level Tracking via Two New Columns
- **Decision**: Add two nullable columns to the `orders` table: `discount_code_id` (FK) and `discount_amount_cents` (int, default 0).
- **Rationale**: Avoids a join table (overkill for one-code-per-order) and follows the inline approach already used for `total`. Storing `discount_amount_cents` separately allows restoration of the original total without a separate `original_total` column.
- **Restore formula**: `order.total += order.discount_amount_cents` then clear both fields.
- **Alternatives considered**: `original_total` column — rejected as redundant; the discount amount is sufficient to reverse the operation.

### Decision 5: Route Placement — New `discounts.py` Router
- **Decision**: New endpoints live in `src/api/routes/discounts.py` with `APIRouter(prefix="/orders", tags=["discounts"])`, included in `main.py`.
- **Rationale**: Endpoints operate on order sub-resources (`/orders/{order_id}/discount-code`) but discount logic is distinct from order CRUD. A dedicated file keeps orders.py focused without requiring a URL prefix change.
- **Alternatives considered**: Adding to `orders.py` — feasible, but would grow the file with unrelated logic.

### Decision 6: Case-Insensitive Code Lookup
- **Decision**: Codes are stored uppercase in the DB; incoming codes are `.upper()`-normalized before lookup.
- **Rationale**: Spec assumption: "discount code lookup is case-insensitive." Normalization at write and read time is the simplest implementation.

### Decision 7: Replace-on-Reapply Semantics
- **Decision**: Applying a new code to an order that already has a code restores the previous discount before applying the new one (atomic swap in a single DB transaction).
- **Rationale**: Spec FR-007 requires one active code at a time; spec edge case says "applying a new code replaces the previous one."

## Resolved Unknowns

All technical unknowns resolved from codebase inspection. No NEEDS CLARIFICATION items remain.
