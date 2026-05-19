---
description: "Task list for discount codes at checkout"
---

# Tasks: Discount Codes at Checkout

**Input**: Design documents from `specs/001-discount-codes/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Explicitly requested in spec ("Include tests"). Test tasks are included and ordered before their corresponding implementation tasks (TDD).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in all descriptions

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data model and seeding infrastructure that ALL user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T001 Add `DiscountCode` SQLAlchemy model to `src/api/models.py` — fields: `id` (Integer PK autoincrement), `code` (String, NOT NULL, UNIQUE), `percentage` (Integer, NOT NULL); use `Mapped[...]` declarative style matching existing models
- [x] T002 Add nullable `discount_code: Mapped[str | None]` column to the `Order` model in `src/api/models.py`; no other columns changed
- [x] T003 [P] Add `seed_discount_codes(db: Session) -> None` to `src/api/main.py` — inserts `[("SAVE5", 5), ("SAVE10", 10), ("SAVE20", 20)]` idempotently (use `db.merge` or `INSERT OR IGNORE` equivalent); call it inside the `lifespan` function after `Base.metadata.create_all`
- [x] T004 [P] Extend the `client` fixture in `tests/conftest.py` to seed `DiscountCode` rows (`SAVE5`/`SAVE10`/`SAVE20`) into the in-memory test DB after table creation; use direct ORM inserts, do not call the main.py function

**Checkpoint**: `DiscountCode` table exists and is seeded in both app startup and tests. `Order` table has `discount_code` column. User story work can begin.

---

## Phase 3: User Story 1 — Apply Valid Discount Code (Priority: P1) 🎯 MVP

**Goal**: A user submitting a recognised discount code at checkout receives an order whose `total` reflects the correct percentage reduction and whose `discount_code` field echoes the normalised code.

**Independent Test**: POST `/orders` with `"discount_code": "SAVE10"` and items totalling 1998 cents → 201 with `total=1798`, `discount_code="SAVE10"`.

### Tests for User Story 1 ⚠️ Write first — ensure they FAIL before implementing T006–T008

- [x] T005 [US1] Add `test_discount_10pct_reduces_total`, `test_discount_5pct_reduces_total`, and `test_discount_20pct_reduces_total` to `tests/test_orders.py`; each test POSTs to `/orders` with the corresponding `discount_code`, asserts HTTP 201, correct `total` in cents, and correct `discount_code` in response

### Implementation for User Story 1

- [x] T006 [US1] Add `discount_code: str | None = None` field to `OrderCreate` Pydantic model in `src/api/routes/orders.py`; add a `field_validator` that strips whitespace and uppercases the value (returns `None` if blank after stripping)
- [x] T007 [US1] Add `discount_code: str | None` field to `OrderOut` Pydantic model in `src/api/routes/orders.py`
- [x] T008 [US1] Implement discount logic in `create_order` in `src/api/routes/orders.py`: after computing `gross_total`, if `discount_code` is set query `DiscountCode` by the uppercased code; if not found raise `HTTPException(422, "Invalid discount code")`; otherwise compute `discount_cents = round(gross_total * dc.percentage / 100)`, set `order.total = gross_total - discount_cents`, set `order.discount_code = dc.code`; if no code, leave `order.total = gross_total` and `order.discount_code = None`

**Checkpoint**: `pytest tests/test_orders.py::test_discount_10pct_reduces_total` (and 5pct, 20pct variants) pass.

---

## Phase 4: User Story 2 — Reject Invalid Discount Code (Priority: P2)

**Goal**: A user submitting an unrecognised or blank discount code receives a 422 error and no order is created.

**Independent Test**: POST `/orders` with `"discount_code": "BOGUS"` → 422 with `detail="Invalid discount code"` and no order row created.

**Note**: No new implementation tasks — T008 already handles the 422 rejection path. This phase adds test coverage only.

### Tests for User Story 2

- [x] T009 [US2] Add `test_invalid_discount_code_returns_422` to `tests/test_orders.py`: POST `/orders` with `"discount_code": "BOGUS"` → assert HTTP 422 and `detail == "Invalid discount code"`
- [x] T010 [US2] Add `test_blank_discount_code_treated_as_none` to `tests/test_orders.py`: POST `/orders` with `"discount_code": "   "` (whitespace-only) → assert HTTP 201 with `discount_code=null` and full undiscounted total (whitespace is normalised to `None` by the validator in T006)

**Checkpoint**: `pytest tests/test_orders.py::test_invalid_discount_code_returns_422` and `test_blank_discount_code_treated_as_none` pass.

---

## Phase 5: User Story 3 — Checkout Without Discount Code (Priority: P3)

**Goal**: Existing checkout behaviour is unaffected when no discount code is provided.

**Independent Test**: POST `/orders` without a `discount_code` field → 201 with unchanged `total` and `discount_code=null`.

**Note**: No new implementation tasks — optional `discount_code=None` is handled naturally by the updated schema. This phase adds a regression test only.

### Tests for User Story 3

- [x] T011 [US3] Add `test_checkout_without_discount_code_unchanged` to `tests/test_orders.py`: POST `/orders` omitting `discount_code` entirely → assert HTTP 201, `total` equals the gross item total, `discount_code` is `null`

**Checkpoint**: All existing `test_orders.py` tests still pass alongside T011.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation and regression confirmation.

- [x] T012 Run `pytest tests/test_orders.py -v` from repo root and confirm all tests (existing 5 + new 7) pass with no failures
- [x] T013 Run the manual validation steps in `specs/001-discount-codes/quickstart.md` against a locally running server to confirm `GET /orders/{id}` also returns `discount_code` correctly

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: No dependencies — start immediately
- **User Stories (Phase 3–5)**: All depend on Phase 2 completion (T001–T004)
- **Polish (Phase 6)**: Depends on all user story phases being complete

### Within Phase 2

- T001 must complete before T002 (same file — sequential)
- T001 must complete before T003 and T004 (model must exist to reference)
- T003 and T004 can run in parallel with each other (different files)

### Within Each User Story Phase

- Tests written **before** implementation (TDD: write → confirm fail → implement → confirm pass)
- T006 before T008 (OrderCreate schema must exist before route logic references it)
- T007 before T008 (OrderOut schema must exist before route handler builds it)
- T006 and T007 are in the same file — sequential

### Parallel Opportunities

```bash
# Phase 2 — after T001+T002 complete:
Task: T003  # seed_discount_codes in main.py
Task: T004  # conftest.py fixture seeding  ← parallel with T003

# Phase 3 — tests can be written while schema tasks are in progress:
# (T005 in tests/test_orders.py, T006/T007 in routes/orders.py — different files)
```

---

## Implementation Strategy

### MVP (User Story 1 only)

1. Complete Phase 2: Foundational (T001–T004)
2. Write US1 tests (T005) — confirm they fail
3. Implement US1 schemas + route logic (T006–T008) — confirm tests pass
4. **STOP and validate**: `pytest tests/test_orders.py -v` green for US1 tests

### Full Delivery (all stories)

1. Phase 2: Foundational
2. Phase 3: US1 — validates discount application
3. Phase 4: US2 — validates rejection (no extra code; tests only)
4. Phase 5: US3 — validates regression (no extra code; test only)
5. Phase 6: Polish — full suite + quickstart validation

---

## Notes

- `[P]` marks tasks that touch different files with no unmet dependencies — safe to run concurrently
- `[Story]` label maps each task to a specific user story for traceability
- US2 and US3 require **test tasks only** — the implementation from US1 (T008) covers both paths
- Blank/whitespace discount codes are normalised to `None` by the Pydantic validator (T006), not rejected with 422 — this makes the no-code path (US3) and the blank-code path behave identically
- All monetary values remain in integer cents throughout; `round()` is applied to the discount calculation to avoid floating-point drift
