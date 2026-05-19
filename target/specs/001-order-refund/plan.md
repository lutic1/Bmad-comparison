# Implementation Plan: Order Refund

**Branch**: `001-order-refund` | **Date**: 2026-05-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-order-refund/spec.md`

## Summary

Add a `POST /orders/{order_id}/refund` endpoint to the existing FastAPI service. The endpoint authenticates via the existing `X-User-Id` header, validates order ownership and a 30-day eligibility window, marks the order as refunded, and returns a refund record. Two new columns (`refunded`, `refunded_at`) are added to the `orders` table. No new dependencies are introduced.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Pydantic v2

**Storage**: SQLite via SQLAlchemy (in-memory SQLite for tests)

**Testing**: pytest + FastAPI TestClient via existing `client` fixture in `tests/conftest.py`

**Target Platform**: Linux server (FastAPI web service)

**Project Type**: web-service (REST API)

**Performance Goals**: N/A — synchronous write to SQLite; no external latency targets defined

**Constraints**: No new third-party dependencies; stdlib `datetime` only. Schema changes require the operator to wipe `app.db` (no migrations).

**Scale/Scope**: Small internal service; single-user auth via `X-User-Id` header.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Technology Stack | ✅ PASS | Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest — no new stack introduced |
| II. Idiomatic FastAPI | ✅ PASS | Single small route function; Pydantic `RefundOut` response model; `Depends(get_current_user)` + `Depends(get_db)` |
| III. Testing (NON-NEGOTIABLE) | ✅ PASS | Happy-path + 5 error-path tests required per FR-007; dedicated `tests/test_refund.py` |
| IV. Conventional Commits | ✅ PASS | Commit will use `feat:` prefix |
| V. Dependency Management | ✅ PASS | Only stdlib `datetime.timedelta`; no new packages |
| VI. Type Safety | ✅ PASS | Full type hints on route handler and `RefundOut` model |
| VII. Focused Changes | ✅ PASS | Only `src/api/models.py`, `src/api/routes/orders.py`, and `tests/test_refund.py` are touched |

**Gate result**: All principles satisfied. No violations. No complexity tracking required.

## Project Structure

### Documentation (this feature)

```text
specs/001-order-refund/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── refund-endpoint.md   # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
src/api/
├── models.py            # Add refunded (bool) + refunded_at (datetime|None) to Order
└── routes/orders.py     # Add POST /{order_id}/refund route + RefundOut Pydantic model

tests/
└── test_refund.py       # New: all refund endpoint tests (happy-path + 5 error paths)
```

**Structure Decision**: Single-project layout. All changes are confined to the existing `src/api/` package. A dedicated test file keeps refund tests isolated from order CRUD tests without introducing new modules or packages.
