---

description: "Task list for Fix Order Date Format"
---

# Tasks: Fix Order Date Format

**Input**: Design documents from `specs/001-fix-order-date-format/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup

No project initialization required. All files exist; no new structure, no
new dependencies, no migrations.

---

## Phase 2: Foundational

No blocking prerequisites. The bug fix is self-contained within existing
files.

---

## Phase 3: User Story 1 — Correct Date Format in Order Responses (Priority: P1) 🎯 MVP

**Goal**: Correct the transposed `%Y-%d-%m` format string to `%Y-%m-%d` in
every location that serializes `created_at`, and update the test assertions
that were written to match the buggy output.

**Independent Test**: Run `pytest tests/test_dates.py -v` — both tests must
pass with correct `YYYY-MM-DD` assertions. Then run the full suite (`pytest`)
to confirm no regressions.

### Implementation for User Story 1

- [x] T001 [P] [US1] Fix format string in `src/api/utils/dates.py` line 5: change `"%Y-%d-%m"` to `"%Y-%m-%d"`
- [x] T002 [P] [US1] Fix format string in `create_order` response in `src/api/routes/orders.py` line 77: change `"%Y-%d-%m"` to `"%Y-%m-%d"`
- [x] T003 [US1] Fix format string in `get_order` response in `src/api/routes/orders.py` line 101: change `"%Y-%d-%m"` to `"%Y-%m-%d"`
- [x] T004 [US1] Fix format string in `_format_created_at` helper in `src/api/routes/orders.py` line 127: change `"%Y-%d-%m"` to `"%Y-%m-%d"`
- [x] T005 [P] [US1] Update test assertion in `tests/test_dates.py` line 8: change expected value from `"2025-07-03"` to `"2025-03-07"`
- [x] T006 [US1] Update test assertion in `tests/test_dates.py` line 13: change expected value from `"2024-31-12"` to `"2024-12-31"`

**Checkpoint**: Run `pytest` — all tests must pass. Story 1 is complete and
independently verifiable.

---

## Phase 4: Polish & Cross-Cutting Concerns

- [x] T007 Run `pytest` (full suite) and confirm zero failures
- [x] T008 Verify `created_at` format with an asymmetric date (day ≠ month) via quickstart.md curl commands

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 3 (US1)**: No prerequisites — can start immediately
- **Phase 4 (Polish)**: Depends on all Phase 3 tasks complete

### Within User Story 1

- T001 and T002 can start in parallel (different files)
- T003 and T004 depend on T002 (same file `orders.py`; edit sequentially)
- T005 can start in parallel with T001/T002 (different file)
- T006 depends on T005 (same file `tests/test_dates.py`; edit sequentially)

### Parallel Opportunities

```bash
# These three can start simultaneously (different files):
Task T001: Fix src/api/utils/dates.py
Task T002: Fix src/api/routes/orders.py (line 77)
Task T005: Fix tests/test_dates.py (line 8)

# Then complete same-file tasks sequentially:
Task T003: Fix src/api/routes/orders.py (line 101)  # after T002
Task T004: Fix src/api/routes/orders.py (line 127)  # after T003
Task T006: Fix tests/test_dates.py (line 13)         # after T005
```

---

## Implementation Strategy

### MVP (Single Story — this entire fix IS the MVP)

1. Complete T001–T006 in parallel/sequential order above
2. Run `pytest tests/test_dates.py` — must pass
3. Run full `pytest` — must pass with no regressions
4. Verify with curl against a running instance (see quickstart.md)

---

## Notes

- [P] tasks touch different files — safe to edit concurrently
- T003, T004 touch `orders.py` after T002 — do these in a single editing session
- T006 touches `tests/test_dates.py` after T005 — do these in a single editing session
- No new files, no new dependencies, no schema changes
- Commit message MUST use `fix:` prefix per Constitution IV
