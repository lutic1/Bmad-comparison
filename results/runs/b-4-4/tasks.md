---

description: "Task list for Percentage Discount Codes at Checkout"
---

# Tasks: Percentage Discount Codes at Checkout

**Input**: Design documents from `/specs/001-discount-codes/`

**Prerequisites**: plan.md (✅), spec.md (✅), research.md (✅), data-model.md (✅), contracts/discount-endpoint.md (✅), quickstart.md (✅)

**Tests**: Included — the feature spec ("Include tests.") and the constitution both require tests for new routes (happy path + at least one error path).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Existing single-project FastAPI layout:

- App: `src/api/` (`models.py`, `deps.py`, `routes/`)
- Tests: `tests/` (uses the `client` fixture in `tests/conftest.py`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm baseline before touching code. The project is already scaffolded (FastAPI + SQLAlchemy + pytest), so setup is minimal.

- [X] T001 Run `pytest -q` from the repo root and confirm the existing suite (`tests/test_users.py`, `tests/test_orders.py`, `tests/test_dates.py`) passes on a clean checkout; record the baseline pass/fail count.
- [X] T002 Remove any stale `app.db` at the repo root (per `CLAUDE.md`: schema is recreated from `Base.metadata` at startup; no migrations).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema and shared constants both user-story phases will depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Add two nullable columns to `Order` in `src/api/models.py` per `specs/001-discount-codes/data-model.md`: `subtotal: Mapped[int | None] = mapped_column(Integer, nullable=True)` and `discount_code: Mapped[str | None] = mapped_column(String(16), nullable=True)`. Keep `total` and all existing columns unchanged.
- [X] T004 In `src/api/routes/orders.py`, add the module-level constant `DISCOUNT_CODES: dict[str, int] = {"SAVE5": 5, "SAVE10": 10, "SAVE20": 20}` near the top of the file (after imports, before the existing router). No behaviour change yet.
- [X] T005 In `src/api/routes/orders.py`, add Pydantic request/response shapes for the new endpoint: `DiscountIn(BaseModel)` with a single field `code: str`, and extend `OrderOut` with optional fields `subtotal: int | None = None` and `discount_code: str | None = None`. Update the two existing `OrderOut(...)` construction sites in `create_order` and `get_order` to pass `subtotal=order.subtotal` and `discount_code=order.discount_code` so they continue to round-trip.
- [X] T006 Register a stub `POST /orders/{order_id}/discount` route in `src/api/routes/orders.py` that resolves the order, enforces ownership (`get_current_user`), and returns the order unchanged. Behaviour for valid/invalid codes is added in the user-story phases below. Use `Depends(get_db)` and `Depends(get_current_user)` like the other handlers in this file.

**Checkpoint**: Schema migrated (via `Base.metadata.create_all` at startup), constant and stub endpoint exist. Existing tests still pass.

---

## Phase 3: User Story 1 — Apply a valid discount code at checkout (Priority: P1) 🎯 MVP

**Goal**: Owner of an order can POST `/orders/{order_id}/discount` with one of `SAVE5` / `SAVE10` / `SAVE20` (case-insensitive) and see the order's `total` reduced by the correct percentage, with `subtotal` and `discount_code` set on the order.

**Independent Test**: Create a user + order with subtotal 100.00, POST `{"code":"SAVE10"}` to `/orders/{id}/discount` as that user, assert response `total == 9000`, `subtotal == 10000`, `discount_code == "SAVE10"`.

### Tests for User Story 1

> Write these tests FIRST, ensure they FAIL before implementation.

- [X] T007 [P] [US1] In `tests/test_discounts.py` add a helper `_make_user_and_order(client, *, email, subtotal_cents)` mirroring the style of `tests/test_orders.py` (`_make_user`); single quantity-1 item with `unit_price` derived from `subtotal_cents / 100`.
- [X] T008 [P] [US1] In `tests/test_discounts.py` add `test_apply_save5_discounts_by_5_percent` — order subtotal 10000 → total 9500, `discount_code == "SAVE5"`, `subtotal == 10000`.
- [X] T009 [P] [US1] In `tests/test_discounts.py` add `test_apply_save10_discounts_by_10_percent` — order subtotal 10000 → total 9000.
- [X] T010 [P] [US1] In `tests/test_discounts.py` add `test_apply_save20_discounts_by_20_percent` — order subtotal 5000 → total 4000.
- [X] T011 [P] [US1] In `tests/test_discounts.py` add `test_apply_discount_is_case_insensitive` — apply `"save10"`, assert response `discount_code == "SAVE10"` and total reduced.
- [X] T012 [P] [US1] In `tests/test_discounts.py` add `test_apply_discount_rounds_half_up` — order subtotal 999, apply `SAVE10`, assert `total == 899` (discount 100 cents, half-up).
- [X] T013 [P] [US1] In `tests/test_discounts.py` add `test_apply_discount_on_zero_subtotal_is_accepted` — by directly creating an `Order` row with subtotal 0 via the existing `/orders` flow with a zero-priced item; assert apply returns 200 and `total == 0` (spec edge case).
- [X] T014 [P] [US1] In `tests/test_discounts.py` add `test_apply_discount_forbidden_for_other_user` — owner creates order; another user POSTs to `/orders/{id}/discount`; assert 403 and order unchanged in a follow-up `GET`.
- [X] T015 [P] [US1] In `tests/test_discounts.py` add `test_apply_discount_unknown_order_returns_404` — POST to `/orders/999/discount` with a valid code; assert 404.
- [X] T016 [P] [US1] In `tests/test_discounts.py` add `test_apply_discount_requires_auth` — POST without `X-User-Id`; assert 401.

### Implementation for User Story 1

- [X] T017 [US1] In `src/api/routes/orders.py`, fill in the `POST /orders/{order_id}/discount` handler for the happy path per `specs/001-discount-codes/contracts/discount-endpoint.md`: uppercase `code`, look up percentage in `DISCOUNT_CODES`, snapshot `order.subtotal = order.total` when `order.subtotal is None`, compute `discount_cents = (order.subtotal * pct + 50) // 100`, set `order.total = order.subtotal - discount_cents` and `order.discount_code = code.upper()`, `db.commit()`, return the updated `OrderOut`. (Error-path branches for invalid codes are added in US2; for now an unknown code can `KeyError` — US2 will replace that with a 400.)
- [X] T018 [US1] Run `pytest tests/test_discounts.py -q` and confirm T008–T016 all pass.

**Checkpoint**: US1 is fully functional and testable independently — valid codes reduce totals; ownership/auth/not-found responses match the existing orders pattern.

---

## Phase 4: User Story 2 — Reject an invalid or unknown discount code (Priority: P2)

**Goal**: Unknown, empty, or malformed codes return HTTP 400 with a clear message and leave the order's `total` / `subtotal` / `discount_code` unchanged.

**Independent Test**: Order with subtotal 10000, POST `{"code":"NOPE123"}` to `/orders/{id}/discount` as the owner → 400 `{"detail":"invalid discount code"}`; follow-up `GET /orders/{id}` still shows `total == 10000` and `discount_code is None`.

### Tests for User Story 2

- [X] T019 [P] [US2] In `tests/test_discounts.py` add `test_apply_unknown_code_returns_400_and_does_not_change_total` — order subtotal 10000; POST `{"code":"NOPE123"}`; assert 400 with `detail == "invalid discount code"`; follow-up `GET /orders/{id}` shows `total == 10000`, `discount_code is None`.
- [X] T020 [P] [US2] In `tests/test_discounts.py` add `test_apply_empty_code_returns_400` — POST `{"code":""}`; assert 400 and total unchanged.
- [X] T021 [P] [US2] In `tests/test_discounts.py` add `test_apply_code_for_unsupported_percentage_returns_400` — POST `{"code":"SAVE15"}`; assert 400 and total unchanged (guards FR-002).

### Implementation for User Story 2

- [X] T022 [US2] In `src/api/routes/orders.py`, in the `POST /orders/{order_id}/discount` handler, before applying any mutation: if `code` is missing, empty after `.strip()`, or `code.strip().upper()` is not a key of `DISCOUNT_CODES`, `raise HTTPException(status_code=400, detail="invalid discount code")`. Ensure no DB writes happen on the rejection path (do the validation before any field assignment / `db.commit()`).
- [X] T023 [US2] Run `pytest tests/test_discounts.py -q` and confirm T019–T021 pass and the US1 tests still pass.

**Checkpoint**: US1 + US2 both work — valid codes apply, invalid codes are rejected cleanly with no side effects.

---

## Phase 5: User Story 3 — Replace a previously applied code (Priority: P3)

**Goal**: Re-applying a different valid code on the same order replaces the first; the new `total` is computed from the **original** subtotal, not the already-discounted total.

**Independent Test**: Order with subtotal 10000, apply `SAVE5` (total 9500), then apply `SAVE20` → final `total == 8000` (20% off 10000), `discount_code == "SAVE20"`, `subtotal == 10000`. Not 7600 (20% off 9500), not 7500 (5%+20% stacked).

### Tests for User Story 3

- [X] T024 [P] [US3] In `tests/test_discounts.py` add `test_apply_second_code_replaces_first` — order subtotal 10000; apply `SAVE5` (assert total 9500); apply `SAVE20`; assert `total == 8000`, `discount_code == "SAVE20"`, `subtotal == 10000`.
- [X] T025 [P] [US3] In `tests/test_discounts.py` add `test_apply_then_invalid_code_keeps_first_discount` — order subtotal 10000; apply `SAVE10` (total 9000); apply `NOPE` → 400; follow-up `GET` still shows `total == 9000`, `discount_code == "SAVE10"`, `subtotal == 10000` (guards FR-005 + FR-007 interaction).

### Implementation for User Story 3

- [X] T026 [US3] Verify the snapshot-on-first-apply logic in `src/api/routes/orders.py` (added in T017) is correct: `subtotal` is set only when `order.subtotal is None`, so a second apply reuses the original snapshot. If T017 was implemented otherwise (e.g., `subtotal` re-derived each call from `total`), adjust to the `if order.subtotal is None:` guard. No new logic should be needed beyond confirming this guard exists.
- [X] T027 [US3] Run `pytest tests/test_discounts.py -q` and confirm T024–T025 pass along with all earlier tests.

**Checkpoint**: All three user stories now pass independently and together.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification against the spec and constitution gates.

- [X] T028 [P] Run the full suite: `pytest -q` from the repo root; confirm all pre-existing tests plus `tests/test_discounts.py` pass.
- [X] T029 [P] Walk through `specs/001-discount-codes/quickstart.md` against a locally running `uvicorn api.main:app` (steps 1–6) and confirm each curl produces the documented response. Reset `app.db` first.
- [X] T030 Re-read `src/api/routes/orders.py` and `src/api/models.py` and confirm: (a) no unrelated refactors slipped in (constitution: "Don't refactor unrelated code"), (b) every new public function / handler has type hints, (c) no new third-party imports were added.
- [X] T031 Confirm coverage on changed files: `pytest --cov=src/api/routes/orders.py --cov=src/api/models.py tests/test_discounts.py tests/test_orders.py` reports ≥80% on the changed lines (constitution gate). If `pytest-cov` is not installed, skip and note in the PR description.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → no dependencies; can start immediately.
- **Foundational (Phase 2)** → depends on Setup; **BLOCKS** all user stories (T003 / T004 / T005 / T006 must all be done before any [US*] task).
- **User Story 1 (Phase 3)** → depends on Foundational; standalone MVP.
- **User Story 2 (Phase 4)** → depends on Foundational; relies on the endpoint stub from T006 and the happy-path handler from T017 to wrap with validation. May start in parallel with US1 as long as T006 is done.
- **User Story 3 (Phase 5)** → depends on Foundational and on T017 (snapshot logic added there). Tests for US3 can be written in parallel with US2 tests once T006 lands.
- **Polish (Phase 6)** → depends on US1 + US2 + US3 being complete.

### User Story Dependencies

- **US1 (P1)**: Foundational only. Delivers the core MVP.
- **US2 (P2)**: Foundational + T017 (it adds the validation guard in front of the existing handler).
- **US3 (P3)**: Foundational + T017 (it relies on the `if order.subtotal is None` snapshot logic introduced in T017; the test in T024 also runs `SAVE5` first which is provided by US1).

### Within Each User Story

- Tests are written and run FIRST, expected to FAIL, then implementation makes them pass.
- Implementation tasks edit shared files (`src/api/routes/orders.py`) — they are sequential within a story, not parallel.

### Parallel Opportunities

- All **Phase 3 test tasks** (T007–T016) are `[P]` — they all touch the same new file `tests/test_discounts.py` but each test function is independent; a single contributor can write them in parallel, or split across contributors with merge coordination on the file.
- **Phase 4 test tasks** (T019–T021) are `[P]` with each other.
- **Phase 5 test tasks** (T024–T025) are `[P]` with each other.
- **Polish tasks** T028 and T029 are `[P]` (different concerns: pytest vs. live uvicorn walkthrough).
- Implementation tasks T017 / T022 / T026 all edit `src/api/routes/orders.py` → must be sequential.

---

## Parallel Example: User Story 1

```bash
# Once Foundational (T003–T006) is done, draft all US1 tests in parallel:
Task: "T008 [US1] test_apply_save5_discounts_by_5_percent in tests/test_discounts.py"
Task: "T009 [US1] test_apply_save10_discounts_by_10_percent in tests/test_discounts.py"
Task: "T010 [US1] test_apply_save20_discounts_by_20_percent in tests/test_discounts.py"
Task: "T011 [US1] test_apply_discount_is_case_insensitive in tests/test_discounts.py"
Task: "T012 [US1] test_apply_discount_rounds_half_up in tests/test_discounts.py"

# Then run them — they should all FAIL — then do T017 (implementation) — then T018 (run, green).
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1: Setup (T001–T002).
2. Complete Phase 2: Foundational (T003–T006). **CRITICAL — blocks all stories.**
3. Complete Phase 3: User Story 1 (T007–T018).
4. **STOP and VALIDATE**: run `pytest tests/test_discounts.py -q`; walk through quickstart steps 1–4.
5. This is a shippable MVP — shoppers can apply valid codes; invalid codes currently `KeyError` (500). Add US2 before exposing externally.

### Incremental Delivery

1. Setup + Foundational → schema and stub endpoint exist.
2. Add US1 → valid codes apply (MVP).
3. Add US2 → invalid codes get a clean 400.
4. Add US3 → users can change their mind without compounding the discount.
5. Polish → full-suite green, coverage check, quickstart walkthrough.

### Parallel Team Strategy

With two contributors after Foundational lands:

- Contributor A: US1 tests + implementation (T007–T018).
- Contributor B: drafts US2 tests (T019–T021) and US3 tests (T024–T025) against the contract; merges after T017 is in.
- Then either contributor picks up T022 (US2 impl) and T026 (US3 verification).

---

## Notes

- `[P]` tasks = different files OR different test functions in the same new file with no shared edits beyond the file header.
- `[Story]` label maps a task to its user story for traceability.
- The constitution gates (≥80% coverage on changed files, happy + error path per route) are checked in T031 and are already satisfied by the test list above.
- No new third-party dependencies are added by any task.
- Existing files outside `src/api/routes/orders.py` and `src/api/models.py` are not modified.
