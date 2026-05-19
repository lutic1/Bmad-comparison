---

description: "Task list for the Order Refund feature (specs/001-order-refund)"
---

# Tasks: Order Refund

**Input**: Design documents from `/specs/001-order-refund/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/refund-endpoint.md, quickstart.md

**Tests**: REQUIRED. The feature spec (SC-004) and the project constitution both mandate automated tests covering the happy path and every error branch enumerated in the spec's Edge Cases.

**Organization**: Tasks are grouped by user story. There is exactly one user story for this feature (US1, priority P1).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Maps to the user story (US1 = "Refund a recent order")
- Each task lists an exact file path

## Path Conventions

Existing FastAPI single-project layout (confirmed in `plan.md` → "Structure Decision"):

- HTTP layer: `src/api/routes/`
- Models: `src/api/models.py`
- Dependencies: `src/api/deps.py`
- Tests: `tests/`

---

## Phase 1: Setup

**Purpose**: Confirm the working tree is green before introducing changes.

- [X] T001 Run `pytest` from the repo root and confirm a clean baseline (all existing tests in `tests/test_users.py`, `tests/test_orders.py`, `tests/test_dates.py` pass). No files modified in this task.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Persist the schema changes that both the implementation and the tests depend on. Required before any US1 task can run.

**Reference**: `specs/001-order-refund/data-model.md`.

- [X] T002 In `src/api/models.py`, add a nullable column `refunded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)` to the existing `Order` model. Do not touch any other field of `Order`.
- [X] T003 In `src/api/models.py`, append a new `Refund` model with: `id` (int PK), `order_id` (ForeignKey to `orders.id`, **unique=True**, not null), `amount` (int, not null — integer cents), `created_at` (DateTime, not null, `default=datetime.utcnow`), and `order: Mapped["Order"] = relationship()`. Match the existing declarative `Mapped[...]` style used by `User`/`Order`/`OrderItem`.

**Checkpoint**: Foundation ready — US1 implementation and tests can now begin.

---

## Phase 3: User Story 1 - Refund a recent order (Priority: P1) 🎯 MVP

**Goal**: An authenticated owner of an order created within the last 30 days can `POST /orders/{order_id}/refund` and receive a refund record; the order is then persistently marked as refunded.

**Independent Test**: Run `pytest tests/test_refunds.py -v` — the happy-path test creates a user, creates an order via `POST /orders`, posts the refund, asserts a 201 with the refund-record JSON, and asserts that `Order.refunded_at` is non-null afterwards.

### Tests for User Story 1 (write FIRST and ensure they FAIL before T010)

> All test tasks edit the same file (`tests/test_refunds.py`), so they are **sequential** — no `[P]` marker. They can be authored together in one editing pass.

- [X] T004 [US1] Create `tests/test_refunds.py`. Add a module-level helper `_create_user_and_order(client, days_ago: int = 0) -> tuple[int, int]` that POSTs `/users` and `/orders` (using `X-User-Id`) via the `client` fixture and returns `(user_id, order_id)`. When `days_ago > 0`, after creating the order, open a DB session via `api.deps.SessionLocal` (or use the override hook in `conftest.py` — match the existing pattern in `tests/test_orders.py`) and back-date `Order.created_at` to `datetime.utcnow() - timedelta(days=days_ago)`. Add the happy-path test `test_refund_eligible_order_returns_201_and_marks_order_refunded`: create a fresh user + order, `POST /orders/{order_id}/refund` with `X-User-Id`, assert status 201, assert response keys `{id, order_id, amount, created_at}` with `order_id` and `amount == order.total`, then re-read the order from the DB and assert `refunded_at is not None`.
- [X] T005 [US1] In `tests/test_refunds.py`, add `test_refund_missing_x_user_id_returns_401`: `POST /orders/1/refund` with **no** `X-User-Id` header → 401, detail contains `"missing X-User-Id header"`.
- [X] T006 [US1] In `tests/test_refunds.py`, add `test_refund_unknown_order_returns_404`: create a user, `POST /orders/9999/refund` with that user's `X-User-Id` → 404, detail `"order not found"`.
- [X] T007 [US1] In `tests/test_refunds.py`, add `test_refund_non_owner_returns_404`: create two users A and B, create an order owned by A, then `POST /orders/{A_order_id}/refund` as B → 404 with detail `"order not found"` (non-disclosure per FR-003 — must NOT be 403).
- [X] T008 [US1] In `tests/test_refunds.py`, add `test_refund_order_older_than_30_days_returns_400`: use the helper to create an order with `days_ago=31`; refund attempt → 400, detail contains `"refund window expired"`.
- [X] T009 [US1] In `tests/test_refunds.py`, add `test_refund_already_refunded_order_returns_409`: refund an eligible order successfully (201), then `POST /orders/{order_id}/refund` again → 409, detail `"order already refunded"`.

### Implementation for User Story 1

- [X] T010 [US1] In `src/api/routes/orders.py`, add the Pydantic response model and the route handler:
  - Add `from datetime import timedelta` and the `Refund` import from `api.models`. Add `from sqlalchemy.exc import IntegrityError`.
  - Add `class RefundOut(BaseModel)` with fields `id: int`, `order_id: int`, `amount: int`, `created_at: str`.
  - Add `@router.post("/{order_id}/refund", response_model=RefundOut, status_code=201)` handler `create_refund(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> RefundOut`. Behavior (matches `specs/001-order-refund/contracts/refund-endpoint.md`):
    1. `order = db.get(Order, order_id)`; if `order is None` **or** `order.user_id != user.id` → `raise HTTPException(404, "order not found")`.
    2. If `datetime.utcnow() - order.created_at > timedelta(days=30)` → `raise HTTPException(400, "refund window expired")`.
    3. If `order.refunded_at is not None` → `raise HTTPException(409, "order already refunded")`.
    4. Construct `refund = Refund(order_id=order.id, amount=order.total)`. `db.add(refund); db.flush()`. Set `order.refunded_at = refund.created_at`. Try `db.commit()`; on `IntegrityError` (concurrent racer) → `db.rollback(); raise HTTPException(409, "order already refunded")`.
    5. `db.refresh(refund)`. Return `RefundOut(id=refund.id, order_id=refund.order_id, amount=refund.amount, created_at=refund.created_at.isoformat())`.
  - Do **not** modify the existing `create_order` or `get_order` handlers; do **not** change `OrderOut`'s date format (constitution: no unrelated refactors).

**Checkpoint**: `pytest tests/test_refunds.py -v` should now be all-green (6 tests). US1 is independently functional and deployable.

---

## Phase 4: Polish & Cross-Cutting Concerns

- [X] T011 Run `pytest tests/test_refunds.py -v` and confirm all six refund tests pass.
- [X] T012 Run the full `pytest` suite from the repo root and confirm zero regressions in `tests/test_users.py`, `tests/test_orders.py`, `tests/test_dates.py`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)** → no deps. Run first.
- **Phase 2 (Foundational)** depends on Phase 1. T003 depends on T002 only insofar as both edit `src/api/models.py` (sequential edits to the same file).
- **Phase 3 (US1)** depends on Phase 2 completion. Within US1:
  - Tests (T004 → T009) are authored before implementation (T010) and are expected to FAIL until T010 lands.
  - All test tasks edit `tests/test_refunds.py` sequentially.
  - T010 implementation is the single change needed to flip the test suite green.
- **Phase 4 (Polish)** depends on T010.

### User Story Dependencies

- **US1 (P1)** is the only user story. No inter-story dependencies.

### Within US1

- T004 must precede T005–T009 (creates the file + helper).
- T005–T009 must precede T010 only as an ordering convention (TDD) — the constitution permits writing handler + tests together, but the task numbering encodes the FAIL-then-pass loop.

### Parallel Opportunities

This feature has very few parallel opportunities because:

- Both foundational tasks edit `src/api/models.py` (sequential).
- All test tasks edit `tests/test_refunds.py` (sequential).
- The implementation is a single file change (T010).

No tasks are marked `[P]`.

---

## Implementation Strategy

### MVP scope

US1 **is** the MVP — there is no scope beyond it for this feature.

1. Phase 1: Setup (T001).
2. Phase 2: Foundational (T002, T003).
3. Phase 3: Write the 6 tests (T004–T009), then implement the handler (T010).
4. Phase 4: Validate (T011, T012).
5. Commit with a `feat:` conventional-commit message (per constitution).

### Notes

- [P] tasks = different files, no dependencies. None in this feature.
- Each test covers exactly one behaviour (per project CLAUDE.md: "Prefer covering one behaviour per test over one giant test").
- Verify tests fail before T010, then pass after.
- Commit after T010 lands (single `feat:` commit is fine; the constitution does not require splitting tests and implementation into separate commits).
- Avoid: editing `OrderOut.created_at` formatting (legacy `%Y-%d-%m` bug — out of scope), adding logging/metrics (constitution forbids), introducing new third-party deps (constitution forbids).
