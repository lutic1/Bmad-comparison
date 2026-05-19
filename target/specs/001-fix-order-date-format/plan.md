# Implementation Plan: Fix Order Date Format

**Branch**: `001-fix-order-date-format` | **Date**: 2026-05-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-fix-order-date-format/spec.md`

## Summary

The `created_at` field in order API responses is formatted with a transposed
format string (`%Y-%d-%m`) that swaps day and month. The fix is a one-line
change in four locations — three in `src/api/routes/orders.py` and one in
`src/api/utils/dates.py` — plus updating two test assertions in
`tests/test_dates.py` that were written to match the buggy output.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Pydantic v2

**Storage**: SQLite via SQLAlchemy (no schema changes)

**Testing**: pytest

**Target Platform**: Linux server (web service)

**Project Type**: web-service

**Performance Goals**: N/A — correctness bug fix, no performance impact

**Constraints**: No new third-party dependencies; stdlib `datetime.strftime` only

**Scale/Scope**: Small REST API — 2 order endpoints, 1 utility function, 1 test file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Stack (Python 3.11+, FastAPI, SQLAlchemy, Pydantic v2, pytest) | ✅ PASS | No stack changes; existing dependencies only |
| II. Idiomatic FastAPI (small routes, Pydantic models, Depends) | ✅ PASS | No route structure changes; `OrderOut` model unchanged |
| III. Testing — 80% coverage, happy-path + error-path per route | ✅ PASS | Existing tests updated; coverage on changed files remains high |
| IV. Conventional Commits (`fix:` prefix) | ✅ PASS | Commit message must use `fix:` |
| V. Dependencies — no new third-party without justification | ✅ PASS | No new dependencies; stdlib `strftime` only |
| VI. Type Hints on every public function and route handler | ✅ PASS | All affected functions already have type hints; none removed |
| VII. Change Discipline — no unrelated refactors | ✅ PASS | Scope limited to format string correction and test assertions |

No violations. Complexity Tracking section omitted.

## Project Structure

### Documentation (this feature)

```text
specs/001-fix-order-date-format/
├── plan.md           # This file
├── research.md       # Phase 0 output
├── data-model.md     # Phase 1 output
├── quickstart.md     # Phase 1 output
├── contracts/
│   └── orders.md     # Phase 1 output
└── tasks.md          # Phase 2 output (/speckit-tasks — not yet created)
```

### Source Code (repository root)

```text
src/
└── api/
    ├── routes/
    │   └── orders.py        # Fix strftime format at lines 77, 101, 127
    └── utils/
        └── dates.py         # Fix strftime format at line 5

tests/
└── test_dates.py            # Update assertions at lines 8, 13
```

**Structure Decision**: Single project, existing layout. No new files or
directories. All changes are in-place corrections to existing files.
