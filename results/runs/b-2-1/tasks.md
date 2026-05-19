---

description: "Task list for Order Refund feature implementation"
---

# Tasks: Order Refund

**Input**: Design documents from `/specs/001-order-refund/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/refund-endpoint.md ✅

**Tests**: REQUIRED per constitution — ≥80% line coverage on changed files; happy-path and at least one error-path test per new route.

**Organization**: Single user story (US1). Foundational schema change must complete before story work begins.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

---

## Phase 1: Foundational (Blocking Prerequisite)

**Purpose**: Schema change that unblocks all story work. Must complete before Phase 2.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T001 Add `refunded: Mapped[bool]` (default `False`, non-nullable) and `refunded_at: Mapped[Optional[datetime]]` (default `None`, nullable) fields to the `Order` class in `src/api/models.py`, following the existing `Mapped[...]` declarative style used for `created_at`

**Checkpoint**: `Order` model has both new fields; existing tests still pass with `pytest`

---

## Phase 2: User Story 1 — Request a Refund (Priority: P1) 🎯 MVP

**Goal**: Authenticated user can POST to `/orders/{order_id}/refund` and receive a refund record, or a clear error for any invalid condition.

**Independent Test**: Run `pytest tests/test_refund.py` — all 6 tests pass and the endpoint is fully exercised.

### Tests for User Story 1 (REQUIRED per constitution) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementing the route**

- [x] T002 [US1] Create `tests/test_refund.py` with all 6 acceptance scenario tests using the `client` fixture from `tests/conftest.py`:
  - `test_refund_success`: POST `/orders/{id}/refund` with valid auth + recent unrefunded order → 200, body contains `order_id`, `refunded_at`, `amount` (= order total in cents)
  - `test_refund_no_auth`: POST without `X-User-Id` header → 401
  - `test_refund_order_not_found`: POST for non-existent order_id → 404
  - `test_refund_wrong_user`: POST with auth header of a different user → 403
  - `test_refund_window_expired`: POST for order with `created_at` set to 31 days ago → 422, detail `"refund window expired"`
  - `test_refund_already_refunded`: POST twice for the same eligible order → second call returns 422, detail `"order already refunded"`

### Implementation for User Story 1

- [x] T003 [US1] Add `RefundOut` Pydantic response model to `src/api/routes/orders.py` with fields: `order_id: int`, `refunded_at: datetime`, `amount: int`; add `from typing import Optional` import if not present

- [x] T004 [US1] Implement `POST /orders/{order_id}/refund` route handler in `src/api/routes/orders.py` following the existing `get_order` pattern:
  - Depend on `get_db` and `get_current_user` (handles FR-001 / 401)
  - `db.get(Order, order_id)` → 404 if None (FR-002)
  - `order.user_id != user.id` → 403 `"forbidden"` (FR-003)
  - `order.refunded` → 422 `"order already refunded"` (FR-005)
  - `(datetime.utcnow() - order.created_at).days > 30` → 422 `"refund window expired"` (FR-004)
  - Set `order.refunded = True`, `order.refunded_at = datetime.utcnow()`, `db.commit()` (FR-006/FR-007)
  - Return `RefundOut(order_id=order.id, refunded_at=order.refunded_at, amount=order.total)` (FR-008)

**Checkpoint**: `pytest tests/test_refund.py` — all 6 tests pass

---

## Phase 3: Polish & Validation

**Purpose**: Confirm no regressions and validate end-to-end behaviour.

- [x] T005 Run `pytest` (full suite) and confirm all tests pass with no regressions
- [x] T006 [P] Manually validate the happy path against `specs/001-order-refund/quickstart.md` with the service running locally

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: No dependencies — start immediately
- **User Story 1 (Phase 2)**: Depends on Phase 1 completion (needs `Order.refunded` + `Order.refunded_at`)
  - T002 (tests): write after T001; tests should fail until T003+T004 are done
  - T003 (model): depends on T001 (imports `Order`)
  - T004 (route): depends on T003 (`RefundOut` must exist)
- **Polish (Phase 3)**: Depends on Phase 2 completion

### Within User Story 1

```
T001 (schema) → T002 (tests, write + verify fail) → T003 (RefundOut model) → T004 (route) → tests pass
```

### Parallel Opportunities

- T005 and T006 in Phase 3 can run in parallel
- No other parallelism in this feature (single file changes, sequential dependencies)

---

## Implementation Strategy

### MVP (the entire feature is one story)

1. Complete Phase 1: add schema fields
2. Write T002 tests — confirm they fail (route doesn't exist yet)
3. Complete T003 + T004 — implement the route
4. Run `pytest tests/test_refund.py` — all 6 tests must pass
5. Run full `pytest` suite — no regressions
6. Feature complete

---

## Notes

- [P] tasks = different files / no inter-dependencies; safe to run concurrently
- [US1] label maps all tasks to the single user story for traceability
- `amount` is always `order.total` in cents — no conversion needed
- The 30-day check uses `.days` on a `timedelta`: `timedelta(days=31).days == 31 > 30` → expired; `timedelta(days=30).days == 30`, which is NOT > 30 → allowed (inclusive boundary per spec)
- Do not wipe `app.db` manually during tests — the `client` fixture already uses in-memory SQLite
