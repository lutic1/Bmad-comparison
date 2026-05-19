---

description: "Task list for Order Refund feature implementation"
---

# Tasks: Order Refund

**Input**: Design documents from `specs/001-order-refund/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/refund.md ✅

**Tests**: Requested in feature specification — test tasks are included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files or no shared dependencies)
- **[Story]**: Which user story this task belongs to (US1 = Successful Refund, US2 = Refund Rejection)
- All tasks include exact file paths

---

## Phase 1: Foundational (Blocking Prerequisites)

**Purpose**: Schema change that both user stories depend on. No user story work can begin until this is done.

- [x] T001 Add `refunded: Mapped[bool]` (default `False`) and `refunded_at: Mapped[Optional[datetime]]` (nullable) to the `Order` class in `src/api/models.py`

**Checkpoint**: `Order` model has the two new columns; `pytest` still passes on existing tests.

---

## Phase 2: User Story 1 — Successful Order Refund (Priority: P1) 🎯 MVP

**Goal**: A user can POST to `/orders/{order_id}/refund` for their own eligible order and receive a `RefundOut` record.

**Independent Test**: Create a user, create an order, immediately call `POST /orders/{id}/refund` with `X-User-Id`, assert HTTP 200 and that the response contains `order_id`, `user_id`, and `refunded_at`.

### Tests for User Story 1 ⚠️ Write these FIRST — they must FAIL before T004/T005

- [x] T002 [P] [US1] Add `test_refund_success` to `tests/test_orders.py`: POST `/orders/{id}/refund` with valid auth returns 200 and correct `RefundOut` JSON (`order_id`, `user_id`, `refunded_at` present)
- [x] T003 [P] [US1] Add `test_refund_at_30_day_boundary` to `tests/test_orders.py`: order with `created_at` set to exactly 30 days ago returns 200 (boundary is inclusive per SC-004)

### Implementation for User Story 1

- [x] T004 [US1] Add `RefundOut` Pydantic model (`order_id: int`, `user_id: int`, `refunded_at: datetime`) to `src/api/routes/orders.py`, alongside existing `OrderOut` (depends on T002, T003)
- [x] T005 [US1] Implement `POST /{order_id}/refund` route in `src/api/routes/orders.py`: authenticate via `Depends(get_current_user)`, fetch order with ownership check (404 if missing or wrong user), check `order.refunded` (409 if already refunded), check `datetime.utcnow() - order.created_at <= timedelta(days=30)` (400 if expired), set `order.refunded = True` and `order.refunded_at = datetime.utcnow()`, commit, return `RefundOut` (depends on T004)

**Checkpoint**: `pytest tests/test_orders.py::test_refund_success tests/test_orders.py::test_refund_at_30_day_boundary` both pass. User Story 1 is independently functional.

---

## Phase 3: User Story 2 — Refund Rejection (Priority: P2)

**Goal**: Every invalid refund attempt returns the correct error code and message. No implementation changes needed — all rejection logic is in T005.

**Independent Test**: Each test below can be run in isolation and verifies exactly one rejection path.

### Tests for User Story 2

- [x] T006 [P] [US2] Add `test_refund_requires_auth` to `tests/test_orders.py`: POST without `X-User-Id` header returns 401
- [x] T007 [P] [US2] Add `test_refund_order_not_found` to `tests/test_orders.py`: POST for a non-existent `order_id` returns 404 with `{"detail": "Order not found"}`
- [x] T008 [P] [US2] Add `test_refund_wrong_owner` to `tests/test_orders.py`: POST for an order belonging to a different user returns 404 (not 403) with `{"detail": "Order not found"}`
- [x] T009 [P] [US2] Add `test_refund_window_expired` to `tests/test_orders.py`: order with `created_at` set to 30 days + 1 second ago returns 400 with `{"detail": "Refund window expired"}`
- [x] T010 [P] [US2] Add `test_refund_already_refunded` to `tests/test_orders.py`: second POST to `/orders/{id}/refund` on an already-refunded order returns 409 with `{"detail": "Order already refunded"}`

**Checkpoint**: All 5 rejection tests pass. `pytest tests/test_orders.py -v` green on all refund tests.

---

## Phase 4: Polish & Validation

- [x] T011 Run `pytest tests/test_orders.py -v` and confirm all refund-related tests pass with zero failures

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: No dependencies — start immediately
- **User Story 1 (Phase 2)**: Depends on Phase 1 completion (Order model columns must exist)
- **User Story 2 (Phase 3)**: Depends on Phase 2 completion (route must exist to test rejection paths)
- **Polish (Phase 4)**: Depends on all user story phases

### Within User Story 1

- T002 and T003 (tests) can run in parallel — write first, confirm they fail
- T004 (RefundOut model) before T005 (route handler)
- T005 implements all guards — authentication, ownership, duplicate, window

### Within User Story 2

- T006, T007, T008, T009, T010 all target different test functions in the same file — all [P], write in any order

---

## Parallel Example: User Story 1

```bash
# Write both happy-path tests together (they touch the same file but are independent functions):
Task: "test_refund_success in tests/test_orders.py"
Task: "test_refund_at_30_day_boundary in tests/test_orders.py"

# Then implement (sequential — T004 before T005):
Task: "Add RefundOut model to src/api/routes/orders.py"
Task: "Implement POST /{order_id}/refund route in src/api/routes/orders.py"
```

## Parallel Example: User Story 2

```bash
# All 5 rejection tests can be written simultaneously:
Task: "test_refund_requires_auth"
Task: "test_refund_order_not_found"
Task: "test_refund_wrong_owner"
Task: "test_refund_window_expired"
Task: "test_refund_already_refunded"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Add Order model columns
2. Complete Phase 2: Write happy-path tests (T002, T003) → Implement RefundOut + route (T004, T005)
3. **STOP and VALIDATE**: `pytest tests/test_orders.py::test_refund_success` passes
4. Feature is usable — authenticated users can refund eligible orders

### Full Delivery

1. Complete MVP (Phase 1 + Phase 2)
2. Add Phase 3: Write 5 rejection-scenario tests (T006–T010) — all should already pass
3. Run Phase 4: Full test suite green

---

## Notes

- [P] tasks within a phase touch different test functions — safe to parallelize
- T005 implements ALL validation guards in one route function; do not split across tasks
- T009 requires manipulating `created_at` at test setup time (set to `datetime.utcnow() - timedelta(days=30, seconds=1)`)
- T003 requires setting `created_at` to `datetime.utcnow() - timedelta(days=30)` to test the inclusive boundary
- No new files created — all changes are in three existing files
