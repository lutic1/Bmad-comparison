---

description: "Task list for order refund feature implementation"
---

# Tasks: Order Refund

**Input**: Design documents from `specs/001-order-refund/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/refund-endpoint.md ✅

**Tests**: Requested — FR-007 mandates happy-path and all error-path scenarios.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in every task description

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema and response model changes required before any user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T001 Add `refunded: Mapped[bool]` (default `False`, non-nullable) and `refunded_at: Mapped[datetime | None]` (nullable) columns to the `Order` class in `src/api/models.py`; import `Boolean` from `sqlalchemy` alongside the existing imports
- [x] T002 [P] Add `RefundOut` Pydantic response model (fields: `order_id: int`, `refunded_at: str`, `total: int`) to `src/api/routes/orders.py`

**Checkpoint**: `Order` model has both new columns; `RefundOut` is importable. Foundation ready — user story work can now begin.

---

## Phase 3: User Story 1 - Successful Refund Request (Priority: P1) 🎯 MVP

**Goal**: Authenticated owner receives a refund record for an eligible order; duplicate refund is rejected.

**Independent Test**: POST refund on a freshly created order → 200 with `RefundOut`; POST again → 409.

> **NOTE: Write tests T003–T004 FIRST and verify they FAIL before implementing T005.**

### Tests for User Story 1 ⚠️

- [x] T003 [P] [US1] Add `test_refund_success` to `tests/test_refund.py`: create a user + order, POST `/orders/{id}/refund` with correct `X-User-Id`, assert 200, body contains `order_id`, `refunded_at`, and `total`
- [x] T004 [P] [US1] Add `test_refund_already_refunded` to `tests/test_refund.py`: create a user + order, POST refund once (assert 200), POST again, assert 409 with `{"detail": "order already refunded"}`

### Implementation for User Story 1

- [x] T005 [US1] Add `POST /{order_id}/refund` route to `src/api/routes/orders.py` using `Depends(get_current_user)` and `Depends(get_db)`; implement checks in this order: 404 if order missing, 403 if wrong owner, 409 if already refunded, 422 if outside 30-day window (`datetime.utcnow() - order.created_at > timedelta(days=30)`); on success set `order.refunded = True`, `order.refunded_at = datetime.utcnow()`, commit, return `RefundOut`

**Checkpoint**: `pytest tests/test_refund.py::test_refund_success tests/test_refund.py::test_refund_already_refunded` — both pass. User Story 1 independently functional.

---

## Phase 4: User Story 2 - Refund Rejected: Ownership Violation (Priority: P2)

**Goal**: Unauthenticated requests, missing orders, and wrong-user attempts are all rejected with the correct status code.

**Independent Test**: POST refund without header → 401; POST for non-existent order → 404; POST for another user's order → 403.

### Tests for User Story 2 ⚠️

- [x] T006 [P] [US2] Add `test_refund_requires_auth` to `tests/test_refund.py`: POST `/orders/1/refund` with no `X-User-Id` header, assert 401
- [x] T007 [P] [US2] Add `test_refund_order_not_found` to `tests/test_refund.py`: create a user, POST `/orders/99999/refund` with their `X-User-Id`, assert 404
- [x] T008 [P] [US2] Add `test_refund_wrong_user` to `tests/test_refund.py`: create two users and an order owned by user 1, POST refund with user 2's `X-User-Id`, assert 403

**Checkpoint**: `pytest tests/test_refund.py::test_refund_requires_auth tests/test_refund.py::test_refund_order_not_found tests/test_refund.py::test_refund_wrong_user` — all pass. User Stories 1 and 2 independently functional.

---

## Phase 5: User Story 3 - Refund Rejected: Expired Window (Priority: P3)

**Goal**: Orders older than 30 days are rejected; an order created exactly 30 days ago is still accepted.

**Independent Test**: POST refund on an order with `created_at` backdated 31 days → 422; backdated exactly 30 days → 200.

### Tests for User Story 3 ⚠️

- [x] T009 [P] [US3] Add `test_refund_expired_window` to `tests/test_refund.py`: create a user + order, manually set `order.created_at` to 31 days ago via the test DB session, POST refund, assert 422 with `{"detail": "refund window expired"}`
- [x] T010 [P] [US3] Add `test_refund_boundary_inclusive` to `tests/test_refund.py`: same setup but backdate `order.created_at` to exactly 30 days ago, POST refund, assert 200

**Checkpoint**: `pytest tests/test_refund.py -v` — all 8 tests pass. All user stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Regression guard and final validation.

- [x] T011 Run full test suite `pytest` from repo root and confirm zero failures across all existing tests (`test_users.py`, `test_orders.py`, `test_dates.py`) plus new `test_refund.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: No dependencies — start immediately
- **User Story 1 (Phase 3)**: Depends on Phase 2 completion (T001, T002)
- **User Story 2 (Phase 4)**: Depends on Phase 3 implementation (T005) being complete
- **User Story 3 (Phase 5)**: Depends on Phase 3 implementation (T005) being complete
- **Polish (Phase 6)**: Depends on all story phases complete

### Within Each User Story

- Tests (T003–T004, T006–T008, T009–T010) MUST be written and FAIL before the relevant implementation task
- US2 and US3 tests (T006–T010) can be written any time after T001–T002; they will fail until T005 is complete

### Parallel Opportunities

- T001 and T002 can run in parallel (different concerns within `orders.py` and `models.py`)
- T003 and T004 can run in parallel (both write to `tests/test_refund.py` — coordinate to avoid conflicts, or write sequentially)
- T006, T007, T008 can run in parallel after T005 is complete
- T009 and T010 can run in parallel after T005 is complete

---

## Parallel Example: User Story 1 Tests

```bash
# Write both test stubs simultaneously (coordinate on test file ownership):
Task: "Add test_refund_success to tests/test_refund.py"
Task: "Add test_refund_already_refunded to tests/test_refund.py"

# Then implement:
Task: "Add POST /{order_id}/refund route to src/api/routes/orders.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundational (T001–T002)
2. Write + fail US1 tests (T003–T004)
3. Complete Phase 3: User Story 1 (T005)
4. **STOP and VALIDATE**: `pytest tests/test_refund.py::test_refund_success tests/test_refund.py::test_refund_already_refunded`
5. Deploy / demo if ready

### Incremental Delivery

1. Foundation (T001–T002) → schema ready
2. US1 implementation (T003–T005) → happy path + duplicate guard
3. US2 tests (T006–T008) → auth and ownership coverage
4. US3 tests (T009–T010) → window enforcement coverage
5. Polish (T011) → regression clean

---

## Notes

- [P] tasks write to different files; coordinate on `tests/test_refund.py` (multiple tasks write there — write sequentially or merge carefully)
- `orders.router` is already registered in `src/api/main.py` — no changes to `main.py` required
- Schema changes (T001) require wiping `app.db` in production; tests use in-memory SQLite and are unaffected
- `timedelta` is available from stdlib `datetime` — no new dependencies needed
- `Boolean` must be imported from `sqlalchemy` alongside existing `DateTime`, `ForeignKey`, `Integer`, `String`
- Verify tests FAIL before T005; verify tests PASS after T005
