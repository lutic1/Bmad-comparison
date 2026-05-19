---

description: "Task list for fix-order-date-format"
---

# Tasks: Fix Order Date Format

**Input**: Design documents from `specs/001-fix-order-date-format/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Test tasks are included — existing tests assert the buggy output and
must be corrected; two new tests are required to lock in the correct format
(per FR-005 and constitution principle III).

**Organization**: Single user story; all tasks map to US1.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1)
- Include exact file paths in descriptions

---

## Phase 1: Setup

No project initialisation is required — this is a bug fix on an existing
codebase. All tools, dependencies, and structure are already in place.

- [x] T001 Confirm baseline: run `pytest` and note which tests currently pass (expect test_dates.py to pass with wrong assertions, test_orders.py to have no date assertions)

---

## Phase 2: Foundational (Blocking Prerequisites)

No foundational infrastructure changes are needed. The fix is entirely in the
serialisation layer; no schema, dependency, or config changes are required.

**Checkpoint**: Proceed directly to User Story 1.

---

## Phase 3: User Story 1 — Correct Date in Order Response (Priority: P1) 🎯

**Goal**: Every order API response returns `created_at` as `YYYY-MM-DD`
(ISO 8601), not the current buggy `YYYY-DD-MM`.

**Independent Test**: Create an order and assert `created_at == "2026-05-18"`
(or any date where day ≠ month). Run `pytest tests/test_dates.py tests/test_orders.py -v`.

### Source fixes for User Story 1

- [x] T002 [P] [US1] Fix format string in `src/api/utils/dates.py` line 5: change `"%Y-%d-%m"` to `"%Y-%m-%d"`
- [x] T003 [P] [US1] Fix format string in `src/api/routes/orders.py` line 77 (inside `create_order`): change `"%Y-%d-%m"` to `"%Y-%m-%d"`
- [x] T004 [P] [US1] Fix format string in `src/api/routes/orders.py` line 101 (inside `get_order`): change `"%Y-%d-%m"` to `"%Y-%m-%d"`
- [x] T005 [P] [US1] Fix format string in `src/api/routes/orders.py` line 127 (inside `_format_created_at`): change `"%Y-%d-%m"` to `"%Y-%m-%d"`

### Test corrections for User Story 1

- [x] T006 [P] [US1] Correct assertion in `tests/test_dates.py::test_format_order_date_basic`: change expected value from `"2025-07-03"` to `"2025-03-07"`
- [x] T007 [P] [US1] Correct assertion in `tests/test_dates.py::test_format_order_date_end_of_year`: change expected value from `"2024-31-12"` to `"2024-12-31"`
- [x] T008 [US1] Add `test_create_order_date_format` to `tests/test_orders.py`: POST an order, assert `body["created_at"]` matches `re.fullmatch(r"\d{4}-\d{2}-\d{2}", ...)` and that day and month are not transposed
- [x] T009 [US1] Add `test_get_order_date_format` to `tests/test_orders.py`: GET an existing order, assert `body["created_at"]` is in `YYYY-MM-DD` format with correct day/month ordering

**Checkpoint**: Run `pytest tests/test_dates.py tests/test_orders.py -v` — all tests must pass before continuing.

---

## Phase 4: Polish & Cross-Cutting Concerns

- [x] T010 Run full test suite `pytest` to confirm no regressions across all test files
- [x] T011 [P] Review `specs/001-fix-order-date-format/quickstart.md` and confirm manual verification steps match the fixed behaviour

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: No blocking work — proceed to Phase 3
- **User Story 1 (Phase 3)**: No prerequisites beyond Phase 1 baseline check
  - T002–T005 (source fixes) can all run in parallel
  - T006–T007 (test corrections) can run in parallel with each other and with source fixes
  - T008–T009 (new tests) should follow T002–T005 to avoid writing tests against unfixed code
- **Polish (Phase 4)**: Depends on all Phase 3 tasks complete

### Within User Story 1

- T002, T003, T004, T005 — fully parallel (different lines/scopes within separate files)
- T006, T007 — parallel with each other and with source fixes
- T008, T009 — parallel with each other; write after source fixes are in place
- T010 — must follow T008 and T009

### Parallel Opportunities

- All source-fix tasks (T002–T005) can run simultaneously
- All test-correction tasks (T006–T007) can run simultaneously
- New test tasks (T008–T009) can run simultaneously

---

## Parallel Example: User Story 1

```bash
# Run all source fixes together (different files/lines):
Task: "Fix format string in src/api/utils/dates.py line 5"
Task: "Fix format string in src/api/routes/orders.py line 77"
Task: "Fix format string in src/api/routes/orders.py line 101"
Task: "Fix format string in src/api/routes/orders.py line 127"

# Run test corrections in parallel:
Task: "Correct assertion in tests/test_dates.py::test_format_order_date_basic"
Task: "Correct assertion in tests/test_dates.py::test_format_order_date_end_of_year"
```

---

## Implementation Strategy

### MVP (User Story 1 only — the only story)

1. T001 — baseline check
2. T002–T007 in parallel — fix all format strings and correct existing test assertions
3. T008–T009 — add new date-format tests to test_orders.py
4. **STOP and VALIDATE**: `pytest tests/test_dates.py tests/test_orders.py -v`
5. T010 — full suite regression check

### Single-pass execution (recommended for this small fix)

All source fixes and test corrections (T002–T007) can be applied in a single
editing pass since they are mechanical substitutions. New tests (T008–T009)
follow immediately after.

---

## Notes

- [P] tasks = different files or independent lines, no shared state
- Tests T006–T007 correct assertions that currently encode the *wrong* behaviour — this is not a new failure, it is a pre-existing wrong expectation
- Use a date where day ≠ month (e.g., `datetime(2026, 5, 18)`) in T008/T009 to ensure the swap bug would be visible if it regressed
- Commit message: `fix: correct order date format to YYYY-MM-DD`
