---

description: "Task list for Order Refund Endpoint"
---

# Tasks: Order Refund Endpoint

**Input**: Design documents from `/specs/001-order-refund/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/refund-endpoint.md, quickstart.md

**Tests**: Tests are mandatory per the project constitution (Principle III): happy-path plus at least one error-path test for every new route. They are included below as first-class tasks.

**Organization**: Tasks are grouped by user story. The three user stories share a single route handler, so US2 (error rules) and US3 (auth) extend the handler introduced in US1. Each story remains independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Different file, no dependency on an incomplete task — safe to run in parallel.
- **[Story]**: US1, US2, US3 — maps to the user story in `spec.md`.

## Path Conventions

Single-project FastAPI layout already in use:

- Routes: `src/api/routes/`
- Models: `src/api/models.py`
- Dependencies: `src/api/deps.py`
- Tests: `tests/`

## Phase 1: Setup

The project is already initialized (FastAPI, SQLAlchemy, pytest configured in `pyproject.toml`). No setup tasks required.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema changes required before any user story can be implemented.

**⚠️ CRITICAL**: All three user stories depend on the `Order.refunded_at` column and the `Refund` model. These tasks MUST complete first.

- [X] T001 Add nullable `refunded_at: Mapped[datetime | None]` column to `Order` in `src/api/models.py` (default `None`, no DB default). Do not modify other `Order` fields.
- [X] T002 Add `Refund` SQLAlchemy model in `src/api/models.py` with `id` (PK), `order_id` (`ForeignKey("orders.id")`, `unique=True`, not null), `created_at: Mapped[datetime]` (default `datetime.utcnow`, not null), and a bidirectional `order`/`refund` relationship to `Order`.

**Checkpoint**: `Base.metadata.create_all` will provision the new column and table on next app/test startup. User stories can now begin.

---

## Phase 3: User Story 1 - Refund an eligible order (Priority: P1) 🎯 MVP

**Goal**: An authenticated owner can refund their order if it was created within the last 30 days, and receives the refund record.

**Independent Test**: Create a user, create an order with `created_at` within 30 days, `POST /orders/{order_id}/refund` with the matching `X-User-Id`. Expect `201`, a refund payload with `id`, `order_id`, `created_at`, and `orders.refunded_at` set in the DB.

### Tests for User Story 1 ⚠️ Write first, ensure they FAIL before implementation

- [X] T003 [P] [US1] Add `tests/test_refunds.py` with `test_refund_recent_order_succeeds`: create a user via `POST /users`, create an order via `POST /orders` (with `X-User-Id`), then `POST /orders/{id}/refund` with the same `X-User-Id`. Assert `status_code == 201`, the response body has `id`, `order_id` matching the created order, and an ISO-format `created_at` string.
- [X] T004 [P] [US1] In `tests/test_refunds.py`, add `test_refund_on_30th_day_boundary_succeeds`: after creating the order, manipulate `Order.created_at` via the SQLAlchemy session (use the `client` fixture's session, or import `SessionLocal` from `api.deps`) to be exactly `datetime.utcnow() - timedelta(days=30, hours=-1)` (just inside the window), then call the refund endpoint and assert `201`.

### Implementation for User Story 1

- [X] T005 [US1] In `src/api/routes/orders.py`, add a `RefundOut(BaseModel)` Pydantic v2 model with fields `id: int`, `order_id: int`, `created_at: datetime` and `model_config = {"from_attributes": True}` (or `class Config: from_attributes = True`, matching the existing style in this file).
- [X] T006 [US1] In `src/api/routes/orders.py`, add the route `@router.post("/{order_id}/refund", response_model=RefundOut, status_code=201)` named `refund_order` that depends on `get_db` and `get_current_user`. Happy-path body only at this point:
  - Load the order with `db.get(Order, order_id)`.
  - Create a `Refund(order_id=order.id)` (let `created_at` default), `db.add` it, `db.flush()` to populate `id`, set `order.refunded_at = refund.created_at`, `db.commit()`, `db.refresh(refund)`.
  - Return `RefundOut.model_validate(refund)`.
  - Full type hints on the handler signature and return type.

**Checkpoint**: Run `pytest tests/test_refunds.py -q` — both US1 tests should pass. The route works for the happy path but does not yet reject invalid requests; US2 adds those guards.

---

## Phase 4: User Story 2 - Reject refund for ineligible order (Priority: P2)

**Goal**: The endpoint rejects refunds for orders that do not exist, belong to another user, are older than 30 days, or are already refunded — without modifying state.

**Independent Test**: Hit the endpoint under each invalid condition and assert the expected status code (404 / 403 / 400 / 409) and that the DB is unchanged.

### Tests for User Story 2 ⚠️ Write first, ensure they FAIL before implementation

- [X] T007 [P] [US2] In `tests/test_refunds.py`, add `test_refund_unknown_order_returns_404`: with an authenticated user, `POST /orders/99999/refund`; assert `status_code == 404` and detail `"order not found"`.
- [X] T008 [P] [US2] In `tests/test_refunds.py`, add `test_refund_not_owner_returns_403`: create user A and user B, create an order as A, attempt the refund with `X-User-Id` set to B; assert `403`, detail `"forbidden"`, and that `orders.refunded_at` is still `None` and no row exists in `refunds`.
- [X] T009 [P] [US2] In `tests/test_refunds.py`, add `test_refund_outside_window_returns_400`: after creating the order, force `Order.created_at = datetime.utcnow() - timedelta(days=31)`; attempt the refund; assert `400`, detail `"refund window expired"`, and DB unchanged.
- [X] T010 [P] [US2] In `tests/test_refunds.py`, add `test_refund_twice_returns_409`: refund once successfully, then call the endpoint again; assert second call returns `409`, detail `"order already refunded"`, and only one `Refund` row exists for that order.

### Implementation for User Story 2

- [X] T011 [US2] In `src/api/routes/orders.py` `refund_order`, add the guards before the insert, in this exact order so each test maps cleanly to one branch:
  1. `if order is None: raise HTTPException(404, "order not found")`
  2. `if order.user_id != user.id: raise HTTPException(403, "forbidden")`
  3. `if order.refunded_at is not None: raise HTTPException(409, "order already refunded")`
  4. `if datetime.utcnow() - order.created_at > timedelta(days=30): raise HTTPException(400, "refund window expired")`
  
  Guards must short-circuit before any `db.add`/`db.commit`, so failed requests do not mutate state. Import `timedelta` alongside the existing `datetime` import.

**Checkpoint**: All US1 + US2 tests pass. The endpoint enforces every business rule from `spec.md` §FR-002–FR-005 and FR-009.

---

## Phase 5: User Story 3 - Reject unauthenticated refund attempt (Priority: P2)

**Goal**: The endpoint rejects callers without a valid `X-User-Id` before any order lookup or state change.

**Independent Test**: Call the endpoint with no `X-User-Id` header and assert `401` with no DB writes.

### Tests for User Story 3 ⚠️ Write first, ensure they FAIL before implementation

- [X] T012 [P] [US3] In `tests/test_refunds.py`, add `test_refund_without_auth_header_returns_401`: create an order (via a separate authenticated request), then `POST /orders/{id}/refund` with **no** `X-User-Id` header; assert `status_code == 401`, detail `"missing X-User-Id header"`, `orders.refunded_at` still `None`, and `refunds` table empty.
- [X] T013 [P] [US3] In `tests/test_refunds.py`, add `test_refund_with_unknown_user_returns_401`: call the endpoint with `X-User-Id: 99999` (no such user); assert `401`, detail `"unknown user"`, and no DB mutation.

### Implementation for User Story 3

- [X] T014 [US3] No new code required: `refund_order` already depends on `get_current_user` (added in T006), which produces the 401 responses asserted by T012/T013. Confirm by running `pytest tests/test_refunds.py::test_refund_without_auth_header_returns_401 tests/test_refunds.py::test_refund_with_unknown_user_returns_401 -q` and verifying both pass with no edits to `src/api/routes/orders.py`.

**Checkpoint**: All three stories pass independently. Feature is complete per `spec.md`.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T015 Run the full test suite from the repo root: `pytest -q`. Confirm all pre-existing tests still pass and no regression was introduced (Principle VII).
- [X] T016 Verify type hints on every public symbol added in this feature (`RefundOut`, `refund_order`, `Refund`). No `Any`, no missing return annotations.
- [X] T017 Walk through `specs/001-order-refund/quickstart.md` manually (or via `httpx` in a one-off script) to confirm the documented curl examples match the implemented behaviour. If anything drifts, fix the implementation (not the quickstart) so the spec remains the source of truth.

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: empty.
- **Phase 2 (Foundational)**: T001 and T002 are independent edits to the same file (`src/api/models.py`) — do them sequentially to avoid edit conflicts; both must finish before any user story.
- **Phase 3 (US1)**: depends on Phase 2.
- **Phase 4 (US2)**: depends on Phase 3 (extends the same handler).
- **Phase 5 (US3)**: depends on Phase 3 (handler signature already wires `get_current_user`). Independent of Phase 4.
- **Phase 6 (Polish)**: depends on Phases 3–5.

### User story dependencies

- **US1 (P1)** is the MVP. The handler skeleton it lands is the precondition for US2 and US3.
- **US2 (P2)** strictly extends US1's handler with guard branches. Cannot start before US1 implementation lands.
- **US3 (P2)** is satisfied for free once US1's `Depends(get_current_user)` is in place; only tests are added.

### Within each user story

- Tests (Txxx [P]) are authored first and confirmed failing.
- Implementation follows in a single file edit.
- Verify story-scoped tests pass before moving to the next story.

### Parallel opportunities

- T003, T004 can be written in parallel (different test functions, same new file — author concurrently then save).
- T007–T010 can be written in parallel for the same reason.
- T012, T013 can be written in parallel.
- T001 and T002 are NOT parallel — same file.
- T005 and T006 are NOT parallel — same file, sequential edits.

---

## Parallel Example: User Story 2 tests

```text
# Author these four test functions concurrently and append to tests/test_refunds.py:
Task: "test_refund_unknown_order_returns_404"      (T007)
Task: "test_refund_not_owner_returns_403"          (T008)
Task: "test_refund_outside_window_returns_400"     (T009)
Task: "test_refund_twice_returns_409"              (T010)
```

---

## Implementation Strategy

### MVP first (US1 only)

1. Phase 2: T001, T002 — schema.
2. Phase 3: T003, T004 (tests RED), then T005, T006 (tests GREEN).
3. STOP and validate — feature works end-to-end for the happy path; deploy/demo if useful.

### Incremental delivery

4. Phase 4: US2 — add guard branches, all error-path tests go GREEN.
5. Phase 5: US3 — add auth tests, verify pre-existing dependency covers them.
6. Phase 6: polish — full suite, type-hint sweep, quickstart walkthrough.

### Notes

- Per `CLAUDE.md`: schema changes do not require migrations; the operator wipes `app.db` between runs.
- Per Principle VII: do not touch unrelated code in `src/api/routes/orders.py` (the existing `create_order`, `get_order`, `_format_created_at`, `adjust_total`, `add_item_inline` helpers stay as-is).
- Per Principle V: no new third-party dependencies.
- Commit cadence: one Conventional Commit per phase is a reasonable default (`feat:`, `test:`).
