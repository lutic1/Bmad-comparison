---

description: "Task list for the 001-order-refund feature"
---

# Tasks: Order Refund

**Input**: Design documents from `/specs/001-order-refund/`

**Prerequisites**: plan.md, spec.md (both required); research.md,
data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included. The feature spec explicitly asks for tests, and the
project constitution requires a happy-path test and at least one
error-path test per new route.

**Organization**: Tasks are grouped by user story so each story can be
implemented and verified independently. All three user stories are P1
(per spec.md).

## Path Conventions

Single-project FastAPI layout (see plan.md → Structure Decision):

- App code: `src/api/`
- Tests: `tests/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project is already initialised (existing FastAPI service).
No setup work is required for this feature.

- [X] T001 Confirm `pytest` runs green on `main` before starting (baseline check, no code changes)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema changes that every user story depends on. All three
user stories need the `Refund` table and `Order.refunded_at` column to
exist before they can be exercised.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Add nullable `refunded_at: Mapped[datetime | None]` column to `Order` in `src/api/models.py` (per data-model.md → Modified: Order)
- [X] T003 Add new `Refund` model (table `refunds`) in `src/api/models.py` with columns `id` PK, `order_id` FK→`orders.id` UNIQUE NOT NULL, `amount` int NOT NULL, `created_at` datetime default `utcnow` NOT NULL; add `Refund.order` relationship and inverse `Order.refund` (uselist=False) per data-model.md → New: Refund

**Checkpoint**: `Base.metadata.create_all` produces the new schema; tests using the existing `client` fixture get the refunds table for free.

---

## Phase 3: User Story 1 — Refund a recent own order (Priority: P1) 🎯 MVP

**Goal**: An authenticated owner of an order created within the last 30
days can call `POST /orders/{order_id}/refund` and receive a refund
record; the order is marked as refunded.

**Independent Test**: Create a user, create an order, call the refund
endpoint with that user's `X-User-Id`; expect HTTP 201 with a
`RefundOut` body whose `order_id` matches and `amount` equals the
order's total. Confirm via DB inspection (or follow-up read) that
`Order.refunded_at` is non-null.

### Tests for User Story 1

> Write the happy-path test first; it should FAIL until T005/T006 are done.

- [X] T004 [P] [US1] Add happy-path test `test_refund_happy_path` in `tests/test_refunds.py` covering: create user → create order → POST `/orders/{id}/refund` with that user's `X-User-Id` → assert 201, body matches `RefundOut` shape, `amount` equals order total, `order_id` matches

### Implementation for User Story 1

- [X] T005 [US1] Add `RefundOut` Pydantic model in `src/api/routes/orders.py` (fields: `id: int`, `order_id: int`, `amount: int`, `created_at: str`; `from_attributes = True`) per contracts/refund.openapi.yaml
- [X] T006 [US1] Implement `POST /orders/{order_id}/refund` handler in `src/api/routes/orders.py`: depends on `get_db` and `get_current_user`; load order via `db.get(Order, order_id)`; on success create `Refund(order_id=..., amount=order.total)`, set `order.refunded_at = datetime.utcnow()`, commit, return `RefundOut` with `status_code=201`. (Rejection branches are wired here too but are validated by US2/US3 tests.)

**Checkpoint**: Happy-path test passes. The refund endpoint exists and
the success branch is fully working. Rejection branches are written but
not yet covered by tests.

---

## Phase 4: User Story 2 — Refund is rejected for ineligible orders (Priority: P1)

**Goal**: The endpoint rejects refunds when the order does not exist,
is owned by another user, is older than 30 days, or has already been
refunded — each with the correct status code and no state change.

**Independent Test**: For each rejection condition, exercise the
endpoint and assert the expected non-2xx status code; assert no
`Refund` row was created and `Order.refunded_at` remained `NULL` (or,
in the already-refunded case, that no second refund row was created).

### Tests for User Story 2

> All four live in the same file (`tests/test_refunds.py`), so they
> share a file and are not marked [P] relative to each other.

- [X] T007 [US2] Add `test_refund_not_found_for_missing_order` in `tests/test_refunds.py`: authenticated user, refund a non-existent order id → expect 404
- [X] T008 [US2] Add `test_refund_not_found_when_owned_by_other_user` in `tests/test_refunds.py`: user A owns the order, user B requests the refund → expect 404 (deliberately not 403, per research.md → status codes)
- [X] T009 [US2] Add `test_refund_rejected_outside_30_day_window` in `tests/test_refunds.py`: create an order then directly back-date its `created_at` to 31 days ago via the test's DB session; request a refund → expect 400
- [X] T010 [US2] Add `test_refund_rejected_when_already_refunded` in `tests/test_refunds.py`: refund successfully once, then refund again → expect 409, and assert only one `Refund` row exists for that `order_id`

### Implementation for User Story 2

> The handler from T006 already contains the rejection branches. These
> tasks confirm/adjust them so the tests above pass.

- [X] T011 [US2] Verify in `src/api/routes/orders.py` that the handler returns: 404 when `order is None`, 404 when `order.user_id != user.id` (NOT 403 — see research.md), 400 when `datetime.utcnow() - order.created_at > timedelta(days=30)`, 409 when `order.refunded_at is not None`. Adjust the handler if any branch differs.

**Checkpoint**: User Story 2 tests pass. All rejection paths covered.

---

## Phase 5: User Story 3 — Unauthenticated requests are refused (Priority: P1)

**Goal**: An unauthenticated caller is refused before any order lookup.

**Independent Test**: POST to the refund endpoint with no `X-User-Id`
header and assert 401; the response must not depend on whether the
order id exists.

### Tests for User Story 3

- [X] T012 [US3] Add `test_refund_requires_auth` in `tests/test_refunds.py`: POST `/orders/1/refund` with no `X-User-Id` header → expect 401. (No order needs to exist; the auth check fires first via `get_current_user`.)

### Implementation for User Story 3

> No new code: `Depends(get_current_user)` already raises 401 when the
> header is missing. T012 is purely a test addition that confirms the
> existing dependency does the right thing for this route.

**Checkpoint**: All three user stories' tests pass independently.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T013 Run `pytest -q` and confirm the full suite (including `tests/test_refunds.py`) passes — 17 passed
- [X] T014 Coverage check: `pytest-cov`/`coverage` not in project dev-deps and constitution forbids new third-party deps without justification; verified manually that every new line/branch in `src/api/routes/orders.py` (refund handler + RefundOut) and `src/api/models.py` (refunded_at column + Refund model + Order.refund relationship) is exercised by at least one test in `tests/test_refunds.py` → 100% line coverage on changed files, ≥80% threshold satisfied

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup; T002 and T003 both touch `src/api/models.py` so run sequentially
- **US1 (Phase 3)**: depends on Foundational; T004 can be written before T005/T006 (it will fail until they land)
- **US2 (Phase 4)**: depends on Foundational + US1's T006 (handler must exist for rejection-branch tests)
- **US3 (Phase 5)**: depends on Foundational + US1's T006 (route must be registered for an unauth test to hit it)
- **Polish (Phase 6)**: depends on US1, US2, US3

### User Story Dependencies

- US1 stands alone after foundational tasks; T004 tests pass after T005+T006.
- US2 and US3 depend on the handler from US1 existing — the project's "one route, one function" pattern (CLAUDE.md) makes splitting the implementation across stories artificial. Tests for US2/US3 are the independent increments.

### Within Each User Story

- US1: write the happy-path test (T004) → add `RefundOut` (T005) → implement the route (T006).
- US2: tests T007–T010 can be written in any order; verify branch behaviour (T011) once they exist.
- US3: single test (T012).

### Parallel Opportunities

- T004 and the implementation tasks T005/T006 touch different files (`tests/test_refunds.py` vs `src/api/routes/orders.py`), so writing the failing test in parallel with implementation is fine. T004 is marked `[P]`.
- T007–T010 all live in `tests/test_refunds.py` → not parallel to each other.
- T011 reads `src/api/routes/orders.py` (no separate edit in the common case) → can run alongside any of T007–T010.
- T013 and T014 are sequential (suite must pass before measuring coverage cleanly).

---

## Parallel Example: User Story 1

```bash
# Two developers, after Phase 2 lands:
# Dev A — writes the failing happy-path test:
Task: "Add happy-path test_refund_happy_path in tests/test_refunds.py"
# Dev B — implements the endpoint:
Task: "Add RefundOut and POST /orders/{order_id}/refund in src/api/routes/orders.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 (T001) — confirm green baseline.
2. Phase 2 (T002, T003) — model + column.
3. Phase 3 (T004–T006) — happy path lands and passes its test.
4. STOP and validate: the refund endpoint works end-to-end for the
   happy path. This is shippable as an MVP.

### Incremental Delivery

1. MVP (US1) → demo.
2. US2 (T007–T011) → all rejection paths covered → demo.
3. US3 (T012) → auth path confirmed → demo.
4. Polish (T013, T014) → suite green, coverage ≥80%.

### Parallel Team Strategy

With two developers, after Phase 2:

- Developer A: T004 + T012 (tests across stories, single test file)
- Developer B: T005 + T006 (implementation in `routes/orders.py`)
- Both converge on T007–T011 in any order once T006 lands.

---

## Notes

- Story labels: [US1] = Happy path, [US2] = Rejection paths, [US3] = Unauth.
- [P] only appears where the tasks touch genuinely different files.
- Every implementation task names the exact file it edits.
- Tests file is `tests/test_refunds.py` (new) — mirrors the
  one-resource-per-file convention used by `test_orders.py` and
  `test_users.py`.
