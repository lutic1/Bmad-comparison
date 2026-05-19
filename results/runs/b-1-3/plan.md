# Implementation Plan: Fix Order Date Format

**Branch**: `001-fix-order-date-format` | **Date**: 2026-05-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-fix-order-date-format/spec.md`

## Summary

Two route handlers in `src/api/routes/orders.py` format `Order.created_at` using
`strftime("%Y-%d-%m")`, which swaps month and day — producing `YYYY-DD-MM` instead
of the ISO 8601 `YYYY-MM-DD`. The fix corrects the format string in both handlers
(and the unused helper). Existing tests gain assertions that verify the date format
and value correctness.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Pydantic v2

**Storage**: SQLite via SQLAlchemy (no schema changes required)

**Testing**: pytest with in-memory SQLite per test (existing `client` fixture)

**Target Platform**: Linux server (FastAPI web service)

**Project Type**: web-service

**Performance Goals**: N/A — bug fix only

**Constraints**: No new dependencies; no database migrations; change is scoped to
format strings in `src/api/routes/orders.py` and assertions in `tests/test_orders.py`

**Scale/Scope**: 2 route handlers, 1 dead-code helper, 1 test file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Stack: Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest | ✅ PASS | No stack changes |
| Idiomatic FastAPI: small routes, Pydantic models, Depends | ✅ PASS | No structural changes to routes |
| Tests non-optional; 80% coverage; happy-path + error-path per route | ✅ PASS | Tests updated per FR-003; existing error-path tests retained |
| Conventional commits: fix: prefix | ✅ PASS | Commit: `fix: correct order created_at date format (YYYY-MM-DD)` |
| No new third-party dependencies | ✅ PASS | Only stdlib `strftime` change |
| Type hints on public functions and route handlers | ✅ PASS | No new public functions |
| Don't refactor unrelated code | ✅ PASS | Change is strictly scoped to format strings and test assertions |

All gates pass. No Complexity Tracking required.

## Project Structure

### Documentation (this feature)

```text
specs/001-fix-order-date-format/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── orders.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
src/
└── api/
    ├── models.py          # Order model (no changes)
    └── routes/
        └── orders.py      # Fix strftime format strings (lines 77, 101, 127)

tests/
└── test_orders.py         # Add created_at format assertions
```

**Structure Decision**: Single project layout. All changes are in two existing files.
