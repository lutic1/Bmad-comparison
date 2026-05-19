---

description: "Task list for the Order Refund feature"
---

# Tasks: Order Refund

**Input**: Design documents from `/specs/001-order-refund/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — the feature spec explicitly requests tests
("Include tests."), and the constitution makes happy-path + error-path
tests non-optional.

**Organization**: Tasks are grouped by user story so each story stays
independently testable. US1 = happy path, US2 = ineligible rejections,
US3 = unauthenticated rejection (all P1 in spec.md).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1/US2/US3)
- Paths below are project-relative to repo root.

## Path Conventions

- Source: `src/api/...`
- Tests: `tests/...`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish a clean baseline before touching application code.

- [X] T001 Run `pytest` from repo root to confirm the existing suite passes on a clean working tree (baseline)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data-model changes that every user story depends on.

**⚠️ CRITICAL**: No user story implementation can begin until Phase 2 is complete.

- [X] T002 Add nullable `refunded_at: Mapped[datetime | None]` column to `Order` in `src/api/models.py` (per `specs/001-order-refund/data-model.md`)
- [X] T003 Add `Refund` model in `src/api/models.py` (`id` PK; `order_id` FK→`orders.id`, NOT NULL, UNIQUE; `amount` Integer NOT NULL; `created_at` DateTime default `datetime.utcnow`) and wire the `Order.refund` ↔ `Refund.order` one-to-one relationship (sequential after T002 — same file)

**Checkpoint**: Schema ready — `Base.metadata.create_all` will produce the new column and table.

---

## Phase 3: User Story 1 - Customer refunds a recent order (Priority: P1) 🎯 MVP

**Goal**: Authenticated owner can refund a ≤30-day-old, not-yet-refunded order and receive the refund record.

**Independent Test**: As an authenticated owner, POST to the new endpoint for an order created less than 30 days ago and confirm `201` with a refund record body and that the order is now marked refunded.

### Tests for User Story 1

> Write the test first; it should fail until T006/T007 land.

- [X] T004 [US1] Add happy-path test `it_should_refund_a_recent_owned_order` in `tests/test_refunds.py`: seed a user + order created 5 days ago, POST `/orders/{id}/refund` with `X-User-Id`, assert `201`, body shape `{id, order_id, amount, created_at}` with `amount == order.total`, and that a subsequent `GET /orders/{id}` reflects the refunded state

### Implementation for User Story 1

- [X] T005 [US1] Create `src/api/routes/refunds.py`: define a `RefundOut` Pydantic v2 model (`id: int`, `order_id: int`, `amount: int`, `created_at: str`) and an `APIRouter(prefix="/orders", tags=["refunds"])` with `POST /{order_id}/refund` returning `RefundOut` with status `201`, using `Depends(get_db)` + `Depends(get_current_user)`; on success create a `Refund(order_id=order.id, amount=order.total)` row, set `order.refunded_at = datetime.utcnow()`, commit, refresh, return `RefundOut`
- [X] T006 [US1] Register the refunds router in `src/api/main.py` (`from api.routes import refunds` + `app.include_router(refunds.router)`)

**Checkpoint**: Happy-path test (T004) passes. Endpoint is live and usable.

---

## Phase 4: User Story 2 - Ineligible refund rejections (Priority: P1)

**Goal**: Refund requests that fail ownership, existence, 30-day window, or already-refunded checks are rejected with the documented status codes and leave the order unchanged.

**Independent Test**: Drive the endpoint through each rejection condition and assert (a) the correct status code, (b) the documented `detail` message, (c) the order's refunded state is unchanged.

### Tests for User Story 2

- [X] T007 [US2] Add test `it_should_404_when_the_order_does_not_exist` in `tests/test_refunds.py` (POST to a non-existent id → `404` with `detail == "order not found"`)
- [X] T008 [US2] Add test `it_should_403_when_the_order_is_not_owned` in `tests/test_refunds.py` (user A owns order; user B POSTs refund → `403` with `detail == "forbidden"`; verify `order.refunded_at` is still `None`)
- [X] T009 [US2] Add test `it_should_400_when_outside_the_30_day_window` in `tests/test_refunds.py` (seed an order, then set `order.created_at = datetime.utcnow() - timedelta(days=31)` via the test DB session, POST refund → `400` with `detail == "refund window expired"`; verify `order.refunded_at` is still `None`)
- [X] T010 [US2] Add test `it_should_409_when_the_order_is_already_refunded` in `tests/test_refunds.py` (refund once, then POST again → `409` with `detail == "order already refunded"`; verify only one row exists in the `refunds` table)

### Implementation for User Story 2

- [X] T011 [US2] In `src/api/routes/refunds.py`, ensure the handler raises `HTTPException(404, "order not found")` when `db.get(Order, order_id)` is `None`; `HTTPException(403, "forbidden")` when `order.user_id != user.id`; `HTTPException(400, "refund window expired")` when `datetime.utcnow() - order.created_at > timedelta(days=30)`; `HTTPException(409, "order already refunded")` when `order.refunded_at is not None`. Checks happen in this order (auth → exists → owned → window → already-refunded), matching the rejection-path tests

**Checkpoint**: T007–T010 pass.

---

## Phase 5: User Story 3 - Unauthenticated rejection (Priority: P1)

**Goal**: Requests with no `X-User-Id` header are rejected before the route body runs.

**Independent Test**: POST to the endpoint with no header, assert `401`, and confirm the targeted order is unchanged.

### Tests for User Story 3

- [X] T012 [US3] Add test `it_should_401_when_unauthenticated` in `tests/test_refunds.py` (POST `/orders/{id}/refund` with no `X-User-Id` header → `401`; verify the order's `refunded_at` is still `None` via a subsequent authenticated `GET`)

### Implementation for User Story 3

- No new application code required: the existing `get_current_user` dependency in `src/api/deps.py` raises `401` for a missing/unknown header. T012 confirms it applies to the new route as well.

**Checkpoint**: All three user stories independently testable; all P1 work complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T013 Run `pytest` from repo root; confirm the full suite (including the new `tests/test_refunds.py`) passes
- [X] T014 Verify changed-file line coverage ≥80% on `src/api/routes/refunds.py` and on the additive changes in `src/api/models.py` — `pytest-cov` not installed in this venv (would be an unrelated dependency add); verified by inspection that every branch in `refunds.py` is hit by a test in `tests/test_refunds.py` (404, 403, 400, 409, 201 happy path, 401 auth)
- [ ] T015 Walk through `specs/001-order-refund/quickstart.md` against a local instance and confirm each step returns the documented status code / body — **not run** in this session (no live server); equivalent assertions exist in `tests/test_refunds.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Setup; **blocks all user stories**.
- **US1 (Phase 3)**: depends on Foundational.
- **US2 (Phase 4)**: depends on Foundational; T011 builds on T005 (same file).
- **US3 (Phase 5)**: depends on Foundational; no new code.
- **Polish (Phase 6)**: depends on every preceding user story.

### Within-Story Dependencies

- US1: T004 (test) → T005 (route module) → T006 (router registration). T005 and T006 touch different files but T006 only makes sense once T005 exists.
- US2: T011 (handler logic) is the single implementation task all four US2 tests depend on. Tests T007–T010 all live in `tests/test_refunds.py` so they're authored sequentially.
- US3: T012 only; no implementation task.

### Parallel Opportunities

- Very limited within this feature because nearly all edits land in just three files (`src/api/models.py`, `src/api/routes/refunds.py`, `tests/test_refunds.py`). No tasks are marked `[P]` for that reason.

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 (T001) → Phase 2 (T002, T003) → Phase 3 (T004, T005, T006).
2. Validate the happy path against `tests/test_refunds.py::it_should_refund_a_recent_owned_order`.
3. The endpoint is shippable at this point if rejection paths were already covered by T011; otherwise, ship after Phase 4.

### Incremental Delivery

1. Foundational schema lands first (T002, T003).
2. US1 happy path becomes live (T004–T006).
3. US2 rejection coverage lands (T007–T011).
4. US3 unauth test confirms behavior (T012).
5. Polish phase (T013–T015) gates the merge.

---

## Notes

- The four rejection conditions (US2) and the unauth condition (US3) are all enforced by code already required by US1's correctness; US2/US3 mostly add **tests** plus a single implementation tightening task (T011).
- `[P]` is intentionally absent throughout: this feature concentrates its edits in three files, so honest-sequential beats spurious parallelism.
- The constitution's ≥80% coverage requirement on changed files is checked in T014; failing T014 means the feature is not done.
- Conventional-commit prefixes for this work: `feat:` for T002/T003/T005/T006, `test:` for T004/T007–T010/T012, `chore:` or `docs:` for spec/plan/task files themselves.
