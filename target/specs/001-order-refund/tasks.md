---

description: "Task list for Order Refund (specs/001-order-refund)"
---

# Tasks: Order Refund

**Input**: Design documents from `/specs/001-order-refund/`

**Prerequisites**: plan.md, spec.md (user stories US1/US2/US3), research.md,
data-model.md, contracts/refund.openapi.yaml, quickstart.md

**Tests**: Included. The feature spec's FR-009 explicitly requires automated
tests for the happy path plus one test per error path in FR-008, and the
project constitution makes tests non-optional.

**Organization**: Tasks are grouped by user story. The route handler is
implemented in the US1 phase (it serves the happy path). US2 and US3 add
test coverage for failure modes the same handler already enforces — no
extra handler code is needed for those stories.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in each description

## Path Conventions

- Single project — existing layout: `src/api/`, `tests/` at repo root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization.

No setup tasks required — the project is already initialized, dependencies
are pinned in `pyproject.toml`, and the test harness (`tests/conftest.py`)
already provides the `client` fixture with an in-memory SQLite per test.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema + Pydantic shapes that every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T001 Add `refunded_at: Mapped[datetime | None]` column to `Order` and add new `Refund` model (id, order_id FK→orders.id, amount int cents, created_at default `datetime.utcnow`) in `src/api/models.py`, including the `order.refund` ↔ `refund.order` relationship per `specs/001-order-refund/data-model.md`
- [X] T002 Add `RefundOut` Pydantic v2 response model (`id: int`, `order_id: int`, `amount: int`, `created_at: datetime`) in `src/api/routes/orders.py`

**Checkpoint**: Schema and response shape ready — user-story handlers and
tests can now be implemented.

---

## Phase 3: User Story 1 - Customer refunds a recent order (Priority: P1) 🎯 MVP

**Goal**: An authenticated owner can refund an order that is within the
30-day window and receives the refund record. The order is marked refunded.

**Independent Test**: Create a user, create an order owned by that user
dated within 30 days, POST `/orders/{id}/refund` with the user's
`X-User-Id`, assert 201 + `RefundOut` body + `Order.refunded_at` is set.

### Implementation for User Story 1

- [X] T003 [US1] Implement `POST /orders/{order_id}/refund` handler in `src/api/routes/orders.py` using `Depends(get_db)` + `Depends(get_current_user)`; validate ownership (404 `"order not found"` if missing or not owned), already-refunded state (409 `"order already refunded"`), 30-day window (422 `"refund window expired"`); on success insert `Refund(order_id, amount=order.total)`, set `order.refunded_at = refund.created_at`, commit, return `RefundOut` with HTTP 201

### Tests for User Story 1

- [X] T004 [US1] Happy-path test `test_refund_recent_order_succeeds`: create user + order ~5 days old, POST refund, assert 201, body matches `RefundOut` (id, order_id, amount == order.total, created_at present), and re-GET shows the refund row + `order.refunded_at` populated — in `tests/test_refunds.py`
- [X] T005 [US1] Boundary test `test_refund_at_29_days_succeeds`: create order with `created_at = utcnow - timedelta(days=29)`, POST refund, assert 201 — in `tests/test_refunds.py`

**Checkpoint**: User Story 1 fully functional and independently testable.
This is the MVP — the feature is shippable here.

---

## Phase 4: User Story 2 - Refund is rejected when the order is too old (Priority: P2)

**Goal**: Orders older than 30 days cannot be refunded; no `Refund` row is
created and the order remains non-refunded.

**Independent Test**: Create an order with `created_at = utcnow -
timedelta(days=31)`, POST refund as the owner, assert 422 + no refund row
+ `order.refunded_at is None`.

### Tests for User Story 2

- [X] T006 [US2] Test `test_refund_after_window_rejected`: backdate order to `utcnow - timedelta(days=31)`, POST refund as owner, assert 422 with detail `"refund window expired"`, assert no `Refund` row exists and `order.refunded_at is None` — in `tests/test_refunds.py`

**Checkpoint**: US1 + US2 both pass.

---

## Phase 5: User Story 3 - Refund is rejected when caller does not own the order (Priority: P2)

**Goal**: Authorization is enforced. Unauthenticated callers are rejected;
authenticated callers refunding someone else's order get an indistinguishable
response from "order does not exist".

**Independent Test**: (a) POST without `X-User-Id` → 401; (b) user B POSTs
refund for user A's order → 404; (c) POST refund for a nonexistent order id
as any authenticated user → 404 (same body as case b).

### Tests for User Story 3

- [X] T007 [US3] Test `test_refund_unauthenticated_rejected`: POST without `X-User-Id`, assert 401 — in `tests/test_refunds.py`
- [X] T008 [US3] Test `test_refund_not_owner_returns_404`: user A creates an order, user B POSTs refund for it, assert 404 with detail `"order not found"`, assert no refund row created — in `tests/test_refunds.py`
- [X] T009 [US3] Test `test_refund_nonexistent_order_returns_404`: authenticated user POSTs refund for `order_id=9999`, assert 404 with detail `"order not found"` (identical to T008's response — confirms the "not yours" vs "not found" indistinguishability assumption) — in `tests/test_refunds.py`

**Checkpoint**: All three user stories pass independently.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Cover the remaining FR-008 failure mode (already-refunded)
and validate the full suite.

- [X] T010 Test `test_refund_already_refunded_returns_409`: refund an eligible order successfully, then POST refund a second time, assert 409 with detail `"order already refunded"`, assert exactly one `Refund` row for that order — in `tests/test_refunds.py`
- [X] T011 Run `pytest tests/test_refunds.py -v` and confirm all 6 tests pass; then run the full suite `pytest -q` to confirm no regressions in `tests/test_orders.py`, `tests/test_users.py`, `tests/test_dates.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: empty — nothing to wait on.
- **Foundational (Phase 2)**: T001 → T002 are independent of each other in
  principle but touch different files; T002 can start immediately after T001
  exists, since `RefundOut` does not reference the ORM model. Both must
  complete before any user-story phase.
- **User Story 1 (Phase 3)**: depends on Phase 2. T003 (handler) must precede
  T004/T005 (tests that call the handler).
- **User Story 2 (Phase 4)**: depends on Phase 3 completing (handler exists).
- **User Story 3 (Phase 5)**: depends on Phase 3 completing.
- **Polish (Phase 6)**: depends on US1 handler being in place.

### User Story Dependencies

- **US1 (P1)**: foundational only — fully self-contained MVP.
- **US2 (P2)**: requires US1's handler. Test-only addition; no new code.
- **US3 (P2)**: requires US1's handler. Test-only addition; no new code.

### Within Each User Story

- For US1: handler (T003) before its tests (T004, T005).
- For US2 / US3: tests only — order does not matter within the phase.

### Parallel Opportunities

- T001 and T002 touch different files — they may run in parallel after
  T001's import surface is decided, but the dependency is light and the
  sequential cost is negligible.
- All test tasks (T004–T010) write to the same file `tests/test_refunds.py`,
  so they are **not** marked [P]; run them sequentially to avoid edit
  conflicts.
- Inside Phase 5, T007/T008/T009 are independent in logic but share the
  test file — sequential.

---

## Parallel Example: Foundational Phase

```bash
# Two independent edits to different files — can be done in one sitting:
Task: "Add Order.refunded_at and Refund model in src/api/models.py"      # T001
Task: "Add RefundOut Pydantic model in src/api/routes/orders.py"         # T002
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 2 (Foundational): T001, T002.
2. Phase 3 (US1): T003, then T004, T005.
3. Run `pytest tests/test_refunds.py -v`. If green → MVP shippable.

### Incremental Delivery

1. MVP as above → demoable end-to-end refund.
2. Add US2 test (T006) → window enforcement covered.
3. Add US3 tests (T007–T009) → authorization coverage.
4. Add Polish (T010) → already-refunded coverage; full FR-008 matrix passes.
5. Run full suite (T011) to confirm no regressions.

### Parallel Team Strategy

Single small feature — best implemented by one developer top-to-bottom.
The phase boundaries still serve as natural code-review checkpoints.

---

## Notes

- [P] tasks = different files, no dependencies. Most refund tests share
  `tests/test_refunds.py` so they are intentionally NOT [P].
- `[Story]` label maps each task to its user story for traceability.
- Per project convention: schema changes do not require migrations
  (`Base.metadata.create_all` at startup; operator wipes `app.db`).
- Avoid touching `tests/test_orders.py`, `tests/test_users.py`, or any
  existing route file beyond `src/api/routes/orders.py` — constitution
  forbids unrelated refactors.
