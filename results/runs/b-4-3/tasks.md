---
description: "Task list for checkout discount code feature"
---

# Tasks: Checkout Discount Code

**Input**: Design documents from `/specs/001-checkout-discount-code/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Included — required by spec FR-010 and constitution Principle III.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files or independent functions, no unresolved dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths included in every task description

## Path Conventions

- Single project: `src/`, `tests/` at repository root
- New route file: `src/api/routes/discounts.py`
- New test file: `tests/test_discounts.py`

---

## Phase 1: Setup

**Purpose**: Scaffold new files so foundational and story tasks can be written in parallel.

- [x] T001 Create `src/api/routes/discounts.py` with `APIRouter(prefix="/orders", tags=["discounts"])` stub and no endpoints yet
- [x] T002 [P] Create `tests/test_discounts.py` with imports (`pytest`, `client` fixture) and a `_make_order` helper that creates a user and an order, returning both IDs

**Checkpoint**: Both files exist; `pytest tests/test_discounts.py` collects 0 tests with no errors.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data model, schema, seeding, and router wiring that ALL user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T003 Add `DiscountCode` model (`id`, `code`, `discount_percent`, `created_at`, `orders` relationship) to `src/api/models.py` using `Mapped[...]` declarative style
- [x] T004 Add `discount_code_id` (FK → discount_codes.id, nullable), `discount_amount_cents` (int, default 0), and `discount_code` relationship to `Order` in `src/api/models.py`
- [x] T005 [P] Extend `OrderOut` in `src/api/routes/orders.py` with two new fields: `discount_code: str | None` and `discount_amount_cents: int` (resolve `discount_code` from the ORM relationship, not the FK id)
- [x] T006 Seed `SAVE5` (5%), `SAVE10` (10%), `SAVE20` (20%) discount codes idempotently in the `lifespan` startup block in `src/api/main.py` (insert only if `code` not already present)
- [x] T007 Import and register the discounts router in `src/api/main.py` via `app.include_router(discounts.router)`

**Checkpoint**: `python -c "from src.api.main import app"` imports cleanly; `Base.metadata.tables` includes `discount_codes`.

---

## Phase 3: User Story 1 — Apply Valid Discount Code (Priority: P1) 🎯 MVP

**Goal**: A user submits a valid discount code and sees the reduced total in the response.

**Independent Test**: `POST /orders/{id}/discount-code` with `{"code": "SAVE10"}` on a $10.00 order returns `total: 900`, `discount_amount_cents: 100`.

> **Write tests before implementation — ensure they FAIL before T012.**

### Tests for User Story 1

- [x] T008 [P] [US1] Write `test_apply_save5_reduces_total_by_5_percent` in `tests/test_discounts.py`: create order with total 1000 cents, POST SAVE5, assert `total == 950` and `discount_amount_cents == 50`
- [x] T009 [P] [US1] Write `test_apply_save10_reduces_total_by_10_percent` in `tests/test_discounts.py`: create order with total 1000 cents, POST SAVE10, assert `total == 900` and `discount_amount_cents == 100`
- [x] T010 [P] [US1] Write `test_apply_save20_reduces_total_by_20_percent` in `tests/test_discounts.py`: create order with total 1000 cents, POST SAVE20, assert `total == 800` and `discount_amount_cents == 200`
- [x] T011 [US1] Write `test_apply_second_code_replaces_first_and_recalculates` in `tests/test_discounts.py`: apply SAVE10 then SAVE20, assert final `total == 800` and `discount_code == "SAVE20"` (recalculated on original 1000, not on 900)

### Implementation for User Story 1

- [x] T012 [US1] Implement `POST /orders/{order_id}/discount-code` in `src/api/routes/discounts.py`: resolve order (404), verify ownership (403), look up code case-insensitively (422 if missing), restore previous discount if any, compute `discount_amount_cents = round(order.total * code.discount_percent / 100)`, apply discount (`total = max(0, total - discount_cents)`), set `discount_code_id`, commit, return `OrderOut`

**Checkpoint**: `pytest tests/test_discounts.py::test_apply_save5_reduces_total_by_5_percent tests/test_discounts.py::test_apply_save10_reduces_total_by_10_percent tests/test_discounts.py::test_apply_save20_reduces_total_by_20_percent tests/test_discounts.py::test_apply_second_code_replaces_first_and_recalculates` all pass.

---

## Phase 4: User Story 2 — Reject Invalid Discount Code (Priority: P2)

**Goal**: A user submits an unrecognized or unauthorized code and receives a clear error; the order total is unchanged.

**Independent Test**: `POST /orders/{id}/discount-code` with `{"code": "FAKE"}` returns 422 with `detail: "invalid discount code"`.

> POST handler is already implemented in T012. This phase adds error-path tests only.

### Tests for User Story 2

- [x] T013 [P] [US2] Write `test_apply_unrecognized_code_returns_422` in `tests/test_discounts.py`: POST `{"code": "FAKE99"}`, assert status 422 and order total unchanged
- [x] T014 [P] [US2] Write `test_apply_without_auth_header_returns_401` in `tests/test_discounts.py`: POST without `X-User-Id` header, assert status 401
- [x] T015 [P] [US2] Write `test_apply_to_other_users_order_returns_403` in `tests/test_discounts.py`: create two users and one order belonging to user 1, POST as user 2, assert status 403
- [x] T016 [P] [US2] Write `test_apply_to_nonexistent_order_returns_404` in `tests/test_discounts.py`: POST to `order_id=99999`, assert status 404

**Checkpoint**: `pytest tests/test_discounts.py -k "US2 or test_apply_unrecognized or test_apply_without or test_apply_to_other or test_apply_to_nonexistent"` all pass.

---

## Phase 5: User Story 3 — Remove Applied Discount Code (Priority: P3)

**Goal**: A user removes a previously applied discount code and the original order total is restored.

**Independent Test**: Apply SAVE10 to a 1000-cent order (total becomes 900), then DELETE discount code, assert `total == 1000` and `discount_code == null`.

> **Write tests before implementation — ensure they FAIL before T019.**

### Tests for User Story 3

- [x] T017 [P] [US3] Write `test_remove_applied_code_restores_original_total` in `tests/test_discounts.py`: apply SAVE10 to 1000-cent order, DELETE discount code, assert `total == 1000`, `discount_code == null`, `discount_amount_cents == 0`
- [x] T018 [P] [US3] Write `test_remove_when_no_code_applied_returns_400` in `tests/test_discounts.py`: DELETE on order with no active code, assert status 400 with `detail: "no discount code applied"`

### Implementation for User Story 3

- [x] T019 [US3] Implement `DELETE /orders/{order_id}/discount-code` in `src/api/routes/discounts.py`: resolve order (404), verify ownership (403), if `discount_code_id` is None raise 400, restore `order.total += order.discount_amount_cents`, set `discount_code_id = None` and `discount_amount_cents = 0`, commit, return `OrderOut`

**Checkpoint**: `pytest tests/test_discounts.py::test_remove_applied_code_restores_original_total tests/test_discounts.py::test_remove_when_no_code_applied_returns_400` pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all user stories.

- [x] T020 Run `pytest tests/test_discounts.py -v` and confirm all 11 tests pass with no warnings
- [x] T021 [P] Verify type hints are present on all public functions and route handlers in `src/api/routes/discounts.py` and on new model fields in `src/api/models.py`
- [x] T022 [P] Run `pytest` (full suite) and confirm no regressions in `tests/test_users.py` or `tests/test_orders.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 — tests must fail before T012
- **User Story 2 (Phase 4)**: Depends on T012 (POST handler) — tests only, no new implementation
- **User Story 3 (Phase 5)**: Depends on Phase 2 — independent of Phases 3 and 4
- **Polish (Phase 6)**: Depends on all story phases complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2
- **US2 (P2)**: Requires T012 complete (POST handler) — tests only
- **US3 (P3)**: Can start after Phase 2, independent of US1 and US2

### Within Each User Story

- Tests MUST be written and confirmed FAILING before implementation tasks
- Implementation tasks commit after all story tests pass
- Verify story independently before moving to next

### Parallel Opportunities

- T001 and T002 can start together (different files)
- T003/T004 (models.py) and T005 (orders.py) can be worked in parallel (different files)
- T008, T009, T010 can be written concurrently (independent test functions)
- T013, T014, T015, T016 can be written concurrently (independent test functions)
- T017, T018 can be written concurrently (independent test functions)
- T021 and T022 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Write all happy-path tests concurrently:
Task: "test_apply_save5_reduces_total_by_5_percent in tests/test_discounts.py"   # T008
Task: "test_apply_save10_reduces_total_by_10_percent in tests/test_discounts.py"  # T009
Task: "test_apply_save20_reduces_total_by_20_percent in tests/test_discounts.py"  # T010

# Then implement:
Task: "POST /orders/{order_id}/discount-code handler in src/api/routes/discounts.py"  # T012
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (model + seed + router wiring)
3. Complete Phase 3: US1 (apply valid code)
4. **STOP and VALIDATE**: `pytest tests/test_discounts.py -k "save5 or save10 or save20 or second_code"` — all pass

### Incremental Delivery

1. Setup + Foundational → Data model ready
2. US1 → Apply discount works → Demo: SAVE10 reduces a $10 order to $9
3. US2 → Error paths covered → Reject typos and unauthorized requests
4. US3 → Remove discount → Full round-trip working
5. Polish → Full suite green, no regressions

---

## Notes

- [P] tasks = different files or independent functions, no blocking dependencies
- [Story] label maps each task to a specific user story for traceability
- Tests MUST fail before implementation (TDD gate enforced at each story checkpoint)
- Integer cents throughout — never float arithmetic on `total` or `discount_amount_cents`
- `discount_code` in `OrderOut` resolves to the code string via ORM relationship, not the FK integer
- Seed codes are idempotent — safe to restart server without duplicating rows
