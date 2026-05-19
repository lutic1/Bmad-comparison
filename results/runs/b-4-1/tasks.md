---
description: "Task list for discount code at checkout"
---

# Tasks: Discount Code at Checkout

**Input**: Design documents from `/specs/001-discount-codes/`

**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, contracts/apply-discount.md ✅, research.md ✅

**Tests**: Included — spec explicitly requested tests; constitution III mandates happy-path + error-path for every new route.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in every task

---

## Phase 1: Setup

**Purpose**: Confirm a clean baseline before any changes are made.

- [x] T001 Run `pytest` and verify all existing tests pass before starting

**Checkpoint**: Green baseline confirmed — feature work can begin.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add the `DiscountCode` model and the FK on `Order` to
`src/api/models.py`. Both user-story phases depend on this schema being
in place.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 Add `DiscountCode` SQLAlchemy model (`id`, `code`, `percentage`, `is_active`) to `src/api/models.py`
- [x] T003 Add nullable `discount_code_id` FK and `discount_code` relationship to `Order` in `src/api/models.py` (depends on T002)

**Checkpoint**: Foundation ready — `DiscountCode` table exists in schema, `Order` has the FK. User story phases can now proceed.

---

## Phase 3: User Story 1 — Apply Valid Discount Code (Priority: P1) 🎯 MVP

**Goal**: A user submits a valid discount code at checkout and receives a
response showing the original subtotal, discount breakdown, and final total.

**Independent Test**: Seed a `DiscountCode` with each tier (5%, 10%, 20%),
create an order, POST to `/orders/{id}/apply-discount`, and assert the
response contains correct `subtotal`, `discount_amount`, and `final_total`.

### Tests for User Story 1 ⚠️ Write FIRST — must FAIL before implementation

- [x] T004 [US1] Write happy-path tests for all three tiers: apply 5%, 10%, and 20% discount codes → 200 with correct `subtotal`, `discount_percentage`, `discount_amount`, `final_total` in `tests/test_orders.py`
- [x] T005 [US1] Write auth/access error tests for the endpoint: missing `X-User-Id` → 401, wrong owner → 403, non-existent order → 404 in `tests/test_orders.py`

### Implementation for User Story 1

- [x] T006 [US1] Add `DiscountApplyRequest` (field: `code: str`) and `OrderWithDiscountOut` (fields: `id`, `user_id`, `subtotal`, `discount_code`, `discount_percentage`, `discount_amount`, `final_total`, `items`, `created_at`) Pydantic models in `src/api/routes/orders.py`
- [x] T007 [US1] Implement `POST /orders/{order_id}/apply-discount` in `src/api/routes/orders.py`: fetch order (404 if missing), check ownership (403), normalise code (`strip().upper()`), look up `DiscountCode`, set `order.discount_code_id`, commit, return `OrderWithDiscountOut` (depends on T006)

**Checkpoint**: User Story 1 is fully functional and independently testable. `pytest tests/test_orders.py -k discount` should pass for T004/T005.

---

## Phase 4: User Story 2 — Reject Invalid Discount Code (Priority: P2)

**Goal**: Submitting a code that does not exist or is inactive returns a
400 with a distinct, descriptive error message; the order total is unchanged.

**Independent Test**: POST with an unknown code → assert 400 `"Invalid discount code"`. POST with an inactive code → assert 400 `"Discount code is no longer active"`. Verify `Order.discount_code_id` remains `None` in both cases.

### Tests for User Story 2 ⚠️ Write FIRST — must FAIL before implementation

- [x] T008 [US2] Write error-path tests: unknown code → 400 `"Invalid discount code"`, inactive code → 400 `"Discount code is no longer active"` in `tests/test_orders.py`

### Implementation for User Story 2

- [x] T009 [US2] Add invalid-code and inactive-code branches to `apply_discount` in `src/api/routes/orders.py`: if `DiscountCode` not found → 400 "Invalid discount code"; if found but `is_active == False` → 400 "Discount code is no longer active" (depends on T007)

**Checkpoint**: User Stories 1 and 2 are both independently functional. All six 400/401/403/404 error paths pass.

---

## Phase 5: User Story 3 — One Discount Code Per Order (Priority: P3)

**Goal**: An order that already has a discount code applied rejects any
further code submission with a clear 400 error.

**Independent Test**: Apply a valid code to an order, then POST a second
code to the same order → assert 400 `"A discount has already been applied to this order"`. Verify the original `discount_code_id` is unchanged.

### Tests for User Story 3 ⚠️ Write FIRST — must FAIL before implementation

- [x] T010 [US3] Write test: apply a valid code then attempt a second code → 400 `"A discount has already been applied to this order"` in `tests/test_orders.py`

### Implementation for User Story 3

- [x] T011 [US3] Add already-applied guard at the top of `apply_discount` (before code lookup): if `order.discount_code_id is not None` → 400 "A discount has already been applied to this order" in `src/api/routes/orders.py` (depends on T009)

**Checkpoint**: All three user stories are independently functional. Full discount feature is complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify quality gates before the feature is considered done.

- [x] T012 Run `pytest tests/test_orders.py -v` and confirm all new and existing order tests pass
- [x] T013 [P] Run full `pytest` suite to verify no regressions across `tests/test_users.py` and `tests/test_dates.py`
- [ ] T014 [P] Manually verify end-to-end flow using `specs/001-discount-codes/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (clean baseline) — **blocks all user stories**
- **User Story 1 (Phase 3)**: Depends on Phase 2 completion
- **User Story 2 (Phase 4)**: Depends on Phase 3 completion (adds branches to same endpoint)
- **User Story 3 (Phase 5)**: Depends on Phase 4 completion (adds guard to same endpoint)
- **Polish (Phase 6)**: Depends on all user story phases complete

### Within Each User Story

- Tests MUST be written and confirmed to FAIL before implementation tasks begin
- Pydantic models (T006) before endpoint implementation (T007)
- Core implementation before error branches (T007 → T009 → T011)

### Parallel Opportunities

- T002 and T003 are sequential (same file; T003 references T002's model)
- T004 and T005 can be written in any order (different test functions, same file — write sequentially to avoid conflicts)
- T012 and T013 can run in parallel (different test files)
- T012, T013, and T014 can all start once Phase 5 is complete

---

## Parallel Example: User Story 1 Tests

```bash
# Both test groups cover different concerns and can be planned in parallel,
# then written sequentially into tests/test_orders.py:
Task: "Happy-path tests for 5%, 10%, 20% tiers" (T004)
Task: "Auth/access error tests 401/403/404" (T005)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Baseline check (T001)
2. Complete Phase 2: Foundational models (T002–T003)
3. Complete Phase 3: User Story 1 (T004–T007)
4. **STOP and VALIDATE**: All three discount tiers return correct breakdowns
5. Ship / demo if ready

### Incremental Delivery

1. Phase 1 + Phase 2 → Foundation ready
2. Phase 3 (US1) → Happy-path apply-discount works → **MVP**
3. Phase 4 (US2) → Error rejection added → Defensively complete
4. Phase 5 (US3) → Duplicate guard added → Fully specified
5. Phase 6 → Quality gates pass → Ready for commit (`feat: add discount code apply endpoint`)

---

## Notes

- [P] = different files or no shared state, can be done in parallel
- [Story] label maps each task to its user story for traceability
- All monetary values in the response are cents (integer) — consistent with existing service convention
- `discount_amount = round(subtotal * percentage / 100)` — use integer arithmetic
- The `apply_discount` handler check order: already-applied guard → code lookup → active check → commit
- Commit message: `feat: add discount code apply endpoint`
