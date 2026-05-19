---
description: "Task list for Order Refund feature implementation"
---

# Tasks: Order Refund

**Input**: Design documents from `specs/001-order-refund/`

**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, contracts/ ✅, research.md ✅

**Tests**: Included — FR-008 mandates automated tests; user input explicitly requested them.

**Files touched**: `src/api/models.py`, `src/api/routes/orders.py`, `tests/test_orders.py`

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different logical units, no shared file conflict)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths included in every task description

---

## Phase 1: Setup

**Purpose**: Confirm baseline before adding any new code.

- [x] T001 Run `pytest tests/ -q` and confirm all existing tests pass (no regressions at baseline)

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: Schema change that every user story's implementation depends on.

**⚠️ CRITICAL**: The route implementation (Phase 3) cannot be completed until this phase is done — the endpoint reads and writes the new columns.

- [x] T002 Add `refunded: Mapped[bool] = mapped_column(default=False)` and `refunded_at: Mapped[datetime | None] = mapped_column(nullable=True)` to the `Order` class in `src/api/models.py`; add `datetime` to imports if not already present

**Checkpoint**: Run `pytest tests/ -q` — all existing tests must still pass (schema is recreated from metadata in-memory per test).

---

## Phase 3: User Story 1 — Successful Refund Request (Priority: P1) 🎯 MVP

**Goal**: Authenticated user can refund an eligible order and receive a `RefundOut` response.

**Independent Test**: `POST /orders/{id}/refund` with a valid user + owned order created within 30 days returns HTTP 200 and a JSON body containing `order_id`, `refunded: true`, and `refunded_at`.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST — they should FAIL before T005/T006 are implemented.**

- [x] T003 [P] [US1] Add `test_refund_success` to `tests/test_orders.py`: create a user + order owned by that user (created_at within 30 days), POST to `/orders/{id}/refund` with `X-User-Id`, assert HTTP 200, body has `order_id == id`, `refunded == true`, `refunded_at` is a non-empty string
- [x] T004 [P] [US1] Add `test_refund_boundary_30_days` to `tests/test_orders.py`: create an order and manually set its `created_at` to exactly `datetime.utcnow() - timedelta(days=30)`, POST to `/orders/{id}/refund`, assert HTTP 200 (boundary is inclusive per research Decision 2)

### Implementation for User Story 1

- [x] T005 [US1] Add `RefundOut(BaseModel)` with fields `order_id: int`, `refunded: bool`, `refunded_at: str` to `src/api/routes/orders.py` (place with other response models near top of file)
- [x] T006 [US1] Implement `POST /orders/{order_id}/refund` handler on the existing `router` in `src/api/routes/orders.py` (depends on T005): signature `def refund_order(order_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> RefundOut`; logic — fetch order by id, raise `HTTPException(404, "order not found")` if missing or `order.user_id != current_user.id`; raise `HTTPException(422, "refund window has expired")` if `datetime.utcnow() - order.created_at > timedelta(days=30)`; raise `HTTPException(422, "order has already been refunded")` if `order.refunded`; set `order.refunded = True`, `order.refunded_at = datetime.utcnow()`, `db.commit()`; return `RefundOut(order_id=order.id, refunded=order.refunded, refunded_at=_format_created_at(order.refunded_at))`

**Checkpoint**: Run `pytest tests/test_orders.py::test_refund_success tests/test_orders.py::test_refund_boundary_30_days -v` — both must pass. User Story 1 is independently functional.

---

## Phase 4: User Story 2 — Refund Rejection on Invalid Conditions (Priority: P2)

**Goal**: Every invalid refund request is rejected with the correct HTTP status and detail message, without leaking order ownership information.

**Independent Test**: Four separate requests (non-existent order, wrong-owner order, expired-window order, already-refunded order) each return the expected status code and `detail` string.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests before verifying them — they require T006 to be complete to pass.**

- [x] T007 [P] [US2] Add `test_refund_order_not_found` to `tests/test_orders.py`: POST to `/orders/99999/refund` with valid `X-User-Id`, assert HTTP 404 and `detail == "order not found"`
- [x] T008 [P] [US2] Add `test_refund_wrong_owner_returns_404` to `tests/test_orders.py`: create two users and one order owned by user 2; POST to `/orders/{id}/refund` with user 1's `X-User-Id`; assert HTTP 404 and `detail == "order not found"` (not 403 — per research Decision 3 / FR-003)
- [x] T009 [P] [US2] Add `test_refund_window_expired` to `tests/test_orders.py`: create an order and set `created_at = datetime.utcnow() - timedelta(days=31)`, POST to `/orders/{id}/refund`, assert HTTP 422 and `detail == "refund window has expired"`
- [x] T010 [P] [US2] Add `test_refund_already_refunded` to `tests/test_orders.py`: create and successfully refund an order (first POST succeeds), then POST to the same endpoint again, assert HTTP 422 and `detail == "order has already been refunded"`

**Checkpoint**: Run `pytest tests/test_orders.py -k "refund" -v` — all 6 refund tests (T003/T004 + T007–T010) must pass.

---

## Phase 5: User Story 3 — Unauthenticated Refund Attempt (Priority: P3)

**Goal**: Requests without valid authentication are rejected before any order lookup occurs.

**Independent Test**: POST to `/orders/{id}/refund` with no `X-User-Id` header returns HTTP 401.

### Tests for User Story 3 ⚠️

- [x] T011 [US3] Add `test_refund_no_auth` to `tests/test_orders.py`: POST to `/orders/1/refund` with no `X-User-Id` header, assert HTTP 401 (reuses existing `get_current_user` behaviour — no new code required)

**Checkpoint**: All 7 new refund tests pass. All user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all stories and cleanup.

- [x] T012 Run `pytest tests/ -q` and confirm all tests (existing + new) pass with zero failures; note final test count for the record

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — run immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 passing. **Blocks Phases 3–5**.
- **User Story 1 (Phase 3)**: Depends on Phase 2. Tests (T003, T004) can be written before T005/T006 but will fail until implementation is complete. Implementation (T005 → T006) must be sequential.
- **User Story 2 (Phase 4)**: Tests depend on T006 existing (endpoint must be implemented). T007–T010 are otherwise fully parallel.
- **User Story 3 (Phase 5)**: Depends on T006 (endpoint must exist to receive the unauthenticated request). T011 is a single task.
- **Polish (Phase 6)**: Depends on all story phases complete.

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 2 only — no dependency on US2 or US3.
- **US2 (P2)**: Depends on Phase 2 + US1 implementation (T006).
- **US3 (P3)**: Depends on Phase 2 + US1 implementation (T006).

### Within Each Phase

- T003 and T004 can be written in parallel (different test functions).
- T005 must complete before T006 (`RefundOut` must exist before the handler returns it).
- T007, T008, T009, T010 can all be written in parallel (independent test functions).

---

## Parallel Execution Examples

### Phase 3 — US1 Tests (write simultaneously)

```
Task: "Add test_refund_success in tests/test_orders.py"
Task: "Add test_refund_boundary_30_days in tests/test_orders.py"
```

### Phase 4 — US2 Tests (write simultaneously)

```
Task: "Add test_refund_order_not_found in tests/test_orders.py"
Task: "Add test_refund_wrong_owner_returns_404 in tests/test_orders.py"
Task: "Add test_refund_window_expired in tests/test_orders.py"
Task: "Add test_refund_already_refunded in tests/test_orders.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Baseline check
2. Complete Phase 2: Add model columns
3. Complete Phase 3: Implement route + US1 tests
4. **STOP and VALIDATE**: `pytest tests/test_orders.py::test_refund_success tests/test_orders.py::test_refund_boundary_30_days -v`
5. Feature core is shippable at this point

### Incremental Delivery

1. Phase 1 + 2 → foundation ready
2. Phase 3 → happy path works (MVP)
3. Phase 4 → all rejection scenarios covered
4. Phase 5 → auth guard validated
5. Phase 6 → clean bill of health

---

## Notes

- [P] tasks involve independent test functions — they edit the same file but add non-conflicting functions, so parallel writing is safe if working in separate editor buffers or agent sub-tasks.
- `_format_created_at` already exists in `src/api/routes/orders.py` — reuse it for `refunded_at` formatting (Decision 6 in research.md).
- Do **not** change the existing `GET /orders/{order_id}` route; its 403-for-wrong-owner behaviour is intentional and out of scope (Decision 3 in research.md).
- `datetime.utcnow()` is already used in `src/api/models.py` for `created_at` defaults — use the same pattern for `refunded_at`.
