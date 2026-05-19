# Implementation Plan: Checkout Discount Code

**Branch**: `001-checkout-discount-code` | **Date**: 2026-05-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-checkout-discount-code/spec.md`

## Summary

Add two endpoints (`POST` and `DELETE` on `/orders/{order_id}/discount-code`) that let authenticated users apply or remove a pre-configured percentage discount code (5%, 10%, or 20%) from an order. Codes are seeded into a new `discount_codes` table at startup; the `orders` table gains two new columns (`discount_code_id`, `discount_amount_cents`) to track the applied discount. All monetary arithmetic follows the existing integer-cents convention.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI 0.115, SQLAlchemy 2.0.35, Pydantic 2.9.2 — all existing; no new dependencies.

**Storage**: SQLite via SQLAlchemy. New table `discount_codes`; two new columns on `orders`. Schema auto-created at startup via `Base.metadata.create_all`. Operator wipes `app.db` on schema changes.

**Testing**: pytest with in-memory SQLite via existing `client` fixture in `tests/conftest.py`.

**Target Platform**: Linux/macOS server (unchanged from existing service).

**Project Type**: Web service (FastAPI REST API).

**Performance Goals**: Standard synchronous FastAPI response times; no special targets for this feature.

**Constraints**: No new third-party dependencies. Integer cents throughout. No float arithmetic on monetary values post-input.

**Scale/Scope**: Same as existing service; feature adds 2 endpoints, 1 new table, 2 new columns.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle                  | Gate                                                          | Status |
|----------------------------|---------------------------------------------------------------|--------|
| I. Technology Stack        | Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest   | ✅ Pass — existing stack only, no new dependencies |
| II. API Design             | Small route functions, Pydantic models, Depends injection     | ✅ Pass — two focused route functions, DiscountCodeApply/OrderOut schemas, get_current_user injected |
| III. Testing               | ≥80% line coverage on changed files; happy-path + error-path per route | ✅ Pass — tests/test_discounts.py covers all 3 user stories |
| IV. Commit Conventions     | feat: prefix for new feature                                  | ✅ Pass — commit will be `feat: add checkout discount code endpoint` |
| V. Dependency Management   | No new third-party dependencies                               | ✅ Pass — no new packages required |
| VI. Type Safety            | Type hints on all public functions and route handlers         | ✅ Pass — all new functions and handlers will be fully typed |
| VII. Scope Discipline      | No unrelated refactoring                                      | ✅ Pass — only discount code feature touched |

**All gates pass. No violations to justify.**

## Project Structure

### Documentation (this feature)

```text
specs/001-checkout-discount-code/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── discount-endpoints.md   # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
src/api/
├── models.py                    # MODIFIED: add DiscountCode model, extend Order
├── main.py                      # MODIFIED: seed discount codes in lifespan, include discounts router
└── routes/
    ├── orders.py                # UNMODIFIED (discount logic in separate file)
    └── discounts.py             # NEW: POST + DELETE /orders/{order_id}/discount-code

tests/
└── test_discounts.py            # NEW: full test coverage for discount feature
```

**Structure Decision**: Single project layout (existing). New router file `discounts.py` keeps discount logic isolated from order CRUD while sharing the `/orders` URL prefix.

## Implementation Notes

### Model changes (`src/api/models.py`)

1. Add `DiscountCode` model (table: `discount_codes`):
   - `id: Mapped[int]` — PK
   - `code: Mapped[str]` — `String(64)`, unique, indexed
   - `discount_percent: Mapped[int]` — 5, 10, or 20
   - `created_at: Mapped[datetime]` — default utcnow
   - `orders: Mapped[list["Order"]]` — relationship back_populates

2. Add to `Order`:
   - `discount_code_id: Mapped[int | None]` — FK → discount_codes.id, nullable, default None
   - `discount_amount_cents: Mapped[int]` — default 0
   - `discount_code: Mapped["DiscountCode | None"]` — relationship, back_populates

### Startup seeding (`src/api/main.py`)

In `lifespan`, after `Base.metadata.create_all`, seed codes idempotently:
```python
SEED_CODES = [("SAVE5", 5), ("SAVE10", 10), ("SAVE20", 20)]
for code_str, pct in SEED_CODES:
    if not db.query(DiscountCode).filter_by(code=code_str).first():
        db.add(DiscountCode(code=code_str, discount_percent=pct))
db.commit()
```

### Route logic (`src/api/routes/discounts.py`)

**POST `/orders/{order_id}/discount-code`**:
1. Resolve order (404 if missing), verify ownership (403).
2. Look up code (case-insensitive, 422 if not found).
3. If discount already applied: restore `order.total += order.discount_amount_cents`.
4. Compute `discount_amount_cents = round(order.total * code.discount_percent / 100)`.
5. Apply: `order.total = max(0, order.total - discount_amount_cents)`.
6. Set `order.discount_code_id`, `order.discount_amount_cents`.
7. Commit and return updated `OrderOut`.

**DELETE `/orders/{order_id}/discount-code`**:
1. Resolve order (404), verify ownership (403).
2. If no discount applied (discount_code_id is None): 400.
3. Restore: `order.total += order.discount_amount_cents`.
4. Clear: `order.discount_code_id = None`, `order.discount_amount_cents = 0`.
5. Commit and return updated `OrderOut`.

### Pydantic schemas

- `DiscountCodeApply(BaseModel)`: `code: str`
- `OrderOut` — extend existing (or redefine in discounts.py) to include `discount_code: str | None` and `discount_amount_cents: int`.

### Test coverage (`tests/test_discounts.py`)

| Test | Story | Path |
|------|-------|------|
| apply valid 5% code → total reduced correctly | US1 | happy |
| apply valid 10% code → total reduced correctly | US1 | happy |
| apply valid 20% code → total reduced correctly | US1 | happy |
| apply code, confirm order → discount_code recorded | US1 | happy |
| apply second code → replaces first, total recalculated | US1 | edge |
| apply invalid code → 422 | US2 | error |
| apply unrecognized code → 422 | US2 | error |
| apply code without auth → 401 | US2 | error |
| apply code to another user's order → 403 | US2 | error |
| remove applied code → total restored | US3 | happy |
| remove when no code applied → 400 | US3 | error |

## Complexity Tracking

> No constitution violations. Section left blank.
