# Implementation Plan: Discount Codes at Checkout

**Branch**: `001-discount-codes` | **Date**: 2026-05-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-discount-codes/spec.md`

## Summary

Allow users to submit an optional discount code when creating an order. Codes
map to fixed percentage discounts (5%, 10%, or 20%). Valid codes reduce the
order total in-place; invalid codes are rejected with 422 before the order is
persisted. Codes are pre-seeded at startup and looked up case-insensitively.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (Mapped declarative), Pydantic v2

**Storage**: SQLite via SQLAlchemy — new `discount_codes` table; `orders` table
gains one nullable `discount_code` column.

**Testing**: pytest with existing `client` fixture (in-memory SQLite, conftest.py)

**Target Platform**: Local/server process (same as existing service)

**Project Type**: web-service (FastAPI REST API)

**Performance Goals**: No new performance constraints; single row lookup on
`discount_codes` by indexed unique `code` column.

**Constraints**: No new third-party dependencies. No migrations — operator
wipes `app.db` between runs. Seed runs idempotently at startup.

**Scale/Scope**: Small single-service change; touches 2 source files and 1
test file.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Technology Stack | ✅ PASS | Python 3.11, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest — no deviations |
| II. API Design | ✅ PASS | Small route function extension; Pydantic models for request/response; Depends for auth |
| III. Testing | ✅ PASS | Happy-path (5%/10%/20%) + error-path (invalid code, blank code) tests required and planned |
| IV. Commit Conventions | ✅ PASS | feat: commit planned; test: commit for test additions |
| V. Dependency Discipline | ✅ PASS | Zero new third-party dependencies |
| VI. Type Safety | ✅ PASS | Type hints on all new/modified public functions and route handlers |
| VII. Scope Discipline | ✅ PASS | Only discount-related code touched; no unrelated refactoring |

**No violations. Complexity Tracking table not required.**

## Project Structure

### Documentation (this feature)

```text
specs/001-discount-codes/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── post-orders.md   # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
src/api/
├── models.py            # ADD: DiscountCode model; ADD: discount_code col on Order
├── main.py              # ADD: seed_discount_codes() call in lifespan
└── routes/
    └── orders.py        # ADD: discount_code to OrderCreate/OrderOut; UPDATE: create_order logic

tests/
└── test_orders.py       # ADD: discount code test cases (happy-path + error-path)
```

**Structure Decision**: Single project, existing layout. No new directories
needed. All changes are additive and contained to the orders domain.

## Implementation Notes (for tasks phase)

These notes resolve ambiguities so the implementer has no open questions:

1. **DiscountCode model** goes in `src/api/models.py` alongside `User`,
   `Order`, `OrderItem`. `code` column: `String`, unique, not null.
   `percentage` column: `Integer`, not null.

2. **Seed function** `seed_discount_codes(db: Session)` inserts
   `[("SAVE5", 5), ("SAVE10", 10), ("SAVE20", 20)]` using
   `INSERT OR IGNORE` / merge-on-conflict so it is idempotent. Called from
   `lifespan` in `main.py` after `Base.metadata.create_all`.

3. **Test seeding**: The `client` fixture in `conftest.py` must also seed
   codes after creating tables. Extend the existing fixture rather than
   duplicating it.

4. **OrderCreate** Pydantic model: add `discount_code: str | None = None`.
   Apply `field_validator` or `model_validator` to strip and uppercase the
   value before it reaches the route handler.

5. **OrderOut** Pydantic model: add `discount_code: str | None`.

6. **create_order route** logic after computing `gross_total`:
   ```
   if discount_code:
       look up DiscountCode by code (uppercased)
       if not found: raise HTTPException(422, "Invalid discount code")
       discount_cents = round(gross_total * percentage / 100)
       order.total = gross_total - discount_cents
       order.discount_code = code  (uppercase)
   else:
       order.total = gross_total
       order.discount_code = None
   ```

7. **GET /orders/{order_id}** response: `OrderOut` already includes
   `discount_code`; no route logic change needed — the ORM will return the
   stored value.
