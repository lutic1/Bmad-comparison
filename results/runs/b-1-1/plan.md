# Implementation Plan: Fix Order Date Format

**Branch**: `001-fix-order-date-format` | **Date**: 2026-05-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-fix-order-date-format/spec.md`

## Summary

The `created_at` field in order API responses uses the format string
`"%Y-%d-%m"`, which transposes day and month, producing `YYYY-DD-MM` instead
of the correct ISO 8601 `YYYY-MM-DD`. The fix is a one-character swap (`%d`↔`%m`)
applied in four locations across two source files, plus correcting two existing
tests that assert the buggy output and adding two new tests to lock in the
correct format on both order endpoints.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Pydantic v2

**Storage**: SQLite via SQLAlchemy (no schema changes needed)

**Testing**: pytest with in-memory SQLite per test (via `conftest.py` fixtures)

**Target Platform**: Linux server (web service)

**Project Type**: web-service

**Performance Goals**: N/A — serialisation-only fix, no measurable overhead

**Constraints**: No new third-party dependencies; fix scope limited to the
date serialisation layer only (constitution principle VII: no unrelated refactoring)

**Scale/Scope**: 2 source files changed, 1 test file corrected, ~6 lines total

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Stack — Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest | ✅ | No stack changes |
| II. Idiomatic FastAPI — small routes, Pydantic models, Depends | ✅ | No route structure changes |
| III. Testing (NON-NEGOTIABLE) — ≥80% coverage, happy-path + error-path | ✅ | Existing tests corrected; 2 new date-format tests added |
| IV. Conventional Commits — `fix:` prefix | ✅ | Commit will use `fix: correct order date format to YYYY-MM-DD` |
| V. Dependencies — no new third-party deps | ✅ | stdlib `datetime.strftime` only |
| VI. Type Hints — on every public function and route handler | ✅ | All touched functions already typed; no new signatures |
| VII. Refactoring Scope — don't refactor unrelated code | ✅ | Only the four format strings and their tests are touched |

**Post-design re-check**: All gates still pass. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-fix-order-date-format/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── order-response.md   # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — not yet created)
```

### Source Code (repository root)

```text
src/
└── api/
    ├── utils/
    │   └── dates.py          # fix: line 5 — format string
    └── routes/
        └── orders.py         # fix: lines 77, 101, 127 — format strings

tests/
├── test_dates.py             # fix: 2 assertions corrected
└── test_orders.py            # add: 2 new date-format tests
```

**Structure Decision**: Single-project layout, existing tree. No new files
or directories in `src/`; one test file corrected, one extended.

## Complexity Tracking

> No constitution violations — this section is intentionally empty.
