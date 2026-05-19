---

description: "Task list template for feature implementation"
---

# Tasks: Fix Order Date Format

**Input**: Design documents from `/specs/001-fix-order-date-format/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Included — constitution mandates tests for every changed file.

**Organization**: Single user story (P1). All tasks are in one phase after the
foundational phase. No setup phase needed (no new project structure required).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1)
- Include exact file paths in descriptions

## Path Conventions

- Single project: `src/`, `tests/` at repository root

---

## Phase 1: Foundational

**Purpose**: No new infrastructure is required. This feature touches two existing
files only. No foundational tasks needed — user story work can begin immediately.

*Skipped — no blocking prerequisites.*

---

## Phase 2: User Story 1 - Correct date format in order responses (Priority: P1) 🎯 MVP

**Goal**: Fix the transposed `%d`/`%m` in `strftime` in both order route handlers
and the dead-code helper, then add `created_at` format assertions to the test suite.

**Independent Test**: Run `pytest tests/test_orders.py -v`; all tests pass and
`created_at` in every response body equals today's date in `YYYY-MM-DD` form.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T001 [P] [US1] Add `created_at` format assertion to `test_create_order_stores_cents` in `tests/test_orders.py` — assert `body["created_at"]` matches regex `^\d{4}-\d{2}-\d{2}$` and equals today's date in YYYY-MM-DD
- [x] T002 [P] [US1] Add `created_at` format assertion to `test_get_order_returns_owner` in `tests/test_orders.py` — assert `resp.json()["created_at"]` matches `^\d{4}-\d{2}-\d{2}$`
- [x] T003 [P] [US1] Add new test `test_create_order_date_format_is_year_month_day` in `tests/test_orders.py` — create an order, mock or freeze date so day ≠ month, assert `created_at` is `YYYY-MM-DD` (not `YYYY-DD-MM`)

### Implementation for User Story 1

- [x] T004 [US1] Fix `strftime` format string in `create_order` handler at line 77 of `src/api/routes/orders.py`: change `"%Y-%d-%m"` → `"%Y-%m-%d"` (depends on T001–T003 failing first)
- [x] T005 [US1] Fix `strftime` format string in `get_order` handler at line 101 of `src/api/routes/orders.py`: change `"%Y-%d-%m"` → `"%Y-%m-%d"`
- [x] T006 [US1] Fix `strftime` format string in dead-code helper `_format_created_at` at line 127 of `src/api/routes/orders.py`: change `"%Y-%d-%m"` → `"%Y-%m-%d"` for consistency

**Checkpoint**: Run `pytest tests/test_orders.py -v` — all tests must pass, including the three new assertions from T001–T003.

---

## Phase 3: Polish & Cross-Cutting Concerns

- [x] T007 [P] Verify `pytest tests/test_orders.py -v` exits 0 with no warnings
- [x] T008 [P] Confirm no other call sites use `"%Y-%d-%m"` — run `grep -r "%Y-%d-%m" src/ tests/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational**: Skipped — no blocking prerequisites
- **User Story 1 (Phase 2)**: Can start immediately
  - Tests (T001–T003) MUST be written and FAIL before implementation (T004–T006)
  - T004–T006 can run in parallel with each other (all touch the same file but are independent edits)
- **Polish (Phase 3)**: After all Phase 2 tasks complete

### Within User Story 1

- T001, T002, T003: Parallel — all are test additions to the same file; write in order but no logic dependency
- T004, T005, T006: Parallel — three independent format-string fixes in `orders.py`
- T007, T008: Parallel — verification tasks after implementation

### Parallel Opportunities

All three test tasks (T001–T003) can be written together. All three implementation
fixes (T004–T006) can be applied together. Tests must fail before fixes are applied.

---

## Parallel Example: User Story 1

```bash
# Step 1 — write tests (they should fail immediately):
# T001: Add assertion to test_create_order_stores_cents
# T002: Add assertion to test_get_order_returns_owner
# T003: Add new test test_create_order_date_format_is_year_month_day

# Verify tests fail:
pytest tests/test_orders.py -v  # expect T001/T002/T003 assertions to fail

# Step 2 — apply all three fixes in orders.py:
# T004: line 77  strftime("%Y-%d-%m") → strftime("%Y-%m-%d")
# T005: line 101 strftime("%Y-%d-%m") → strftime("%Y-%m-%d")
# T006: line 127 strftime("%Y-%d-%m") → strftime("%Y-%m-%d")

# Verify all tests pass:
pytest tests/test_orders.py -v  # expect all green
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Write test assertions (T001–T003) — confirm they fail
2. Apply format-string fixes (T004–T006) — confirm tests pass
3. Run polish checks (T007–T008)
4. **STOP and VALIDATE**: `pytest tests/test_orders.py -v` all green
5. Commit: `fix: correct order created_at date format (YYYY-MM-DD)`

---

## Notes

- [P] tasks = different files or independent edits, no unresolved dependencies
- [US1] label maps every task to User Story 1 from spec.md
- Tests MUST be written before fixes and MUST fail first (red-green cycle)
- Only `src/api/routes/orders.py` and `tests/test_orders.py` are touched — no other files
- Do NOT change `OrderOut.created_at: str` type annotation — it is already correct
- Do NOT remove `_format_created_at` — fixing it is sufficient and removing it is out of scope
