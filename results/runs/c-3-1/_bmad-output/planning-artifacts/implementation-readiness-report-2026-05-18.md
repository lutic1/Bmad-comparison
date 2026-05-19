---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-target-2026-05-18/prd.md
  - _bmad-output/planning-artifacts/architecture.md
assessor: Product Owner (bmad-check-implementation-readiness)
date: 2026-05-18
project: target
---

# Implementation Readiness Assessment Report

**Date:** 2026-05-18
**Project:** target
**Feature:** API Rate Limiting

---

## Step 1 — Document Discovery

| Document Type | Status | Path |
|---|---|---|
| PRD | ✅ Found | `_bmad-output/planning-artifacts/prds/prd-target-2026-05-18/prd.md` |
| Architecture | ✅ Found | `_bmad-output/planning-artifacts/architecture.md` |
| Epics & Stories | ⚪ Not yet created | — (this check is pre-story-creation) |
| UX Design | ⚪ Not applicable | Pure API feature, no UI |

**Note on scope:** No epics exist yet — the user's intent is to verify that PRD + architecture together are sufficient to slice into stories. Epic quality review is therefore N/A at this stage.

---

## Step 2 — PRD Analysis

### Functional Requirements Extracted

| ID | Requirement |
|---|---|
| FR-1 | Count requests per client identity within a rolling window; reject requests exceeding the threshold with 429 |
| FR-2 | Identity key: `X-User-Id` header value for authenticated endpoints; source IP for unauthenticated endpoints |
| FR-3 | 429 response: status 429, `Retry-After` header (positive int seconds), JSON body `{"detail": "Rate limit exceeded. Retry after {N} seconds."}` |
| FR-4 | `GET /health` is exempt from rate limiting |
| FR-5 | Configuration via `RATE_LIMIT_REQUESTS` (default 60) and `RATE_LIMIT_WINDOW_SECONDS` (default 60) env vars |

**Total FRs: 5**

### Non-Functional Requirements Extracted

| ID | Requirement |
|---|---|
| NFR-1 | Rate limiter adds < 1 ms p99 latency on non-limited (pass-through) path |
| NFR-2 | Rate limiter must not raise an unhandled exception under concurrent load; must fail open (allow request) rather than return 500 |

**Total NFRs: 2**

### PRD Completeness Assessment

The PRD is well-formed. All five FRs carry explicit testable consequences. Both NFRs are measurable (latency budget) or behaviourally precise (fail-open semantics). All six open questions from elicitation are resolved in the architecture document. No `[ASSUMPTION]` tags remain unresolved. The PRD is complete as an input document.

---

## Step 3 — FR Coverage Against Architecture

No epics document exists yet. This section validates that the architecture document covers every FR before story creation begins.

| FR | PRD Requirement Summary | Architecture Coverage | Status |
|---|---|---|---|
| FR-1 | Per-identity rate limit with window counter | AD-4 (fixed-window algorithm, `_store` dict, threading.Lock) | ✅ Covered |
| FR-2 | Dual identity key | AD-3 (unified key: X-User-Id if present, else IP) | ✅ Covered |
| FR-3 | 429 + Retry-After + JSON body | §3 `rate_limit.py` implementation — status 429, `Retry-After` header, f-string detail | ✅ Covered |
| FR-4 | Health endpoint exempt | AD-2 (router-level Depends; `/health` on `app` directly, never touches rate limiter) | ✅ Covered |
| FR-5 | Env var configuration | AD-6 (`RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS` at module import) | ✅ Covered |
| NFR-1 | < 1 ms p99 latency | AD-4 (lock + dict lookup is O(1); fail-fast path) | ✅ Addressed |
| NFR-2 | Fail open | AD-5 (try/except wraps counter logic; HTTPException re-raised explicitly) | ✅ Covered |

**Coverage: 7 / 7 (100%)**

---

## Step 4 — UX Alignment

No UX document exists, and none is required. This feature has no user interface — it is a server-side enforcement mechanism. The only consumer-visible artefact is the `429` response shape, which is fully specified in FR-3 and confirmed in the architecture's implementation code.

**UX alignment: N/A — no gap.**

---

## Step 5 — Implementation Readiness Quality Review

### ✅ Passing checks

- **Files changed are enumerated precisely:** 2 new files (`rate_limit.py`, `test_rate_limit.py`), 2 one-line edits (`users.py`, `orders.py`). No ambiguity about scope.
- **Full implementation provided:** `rate_limit.py` is written out completely in the architecture doc. Story author has no design decisions to make.
- **8 named test cases specified:** Each test has a clear description of what it asserts.
- **Env-var override test included:** `test_env_var_override` covers FR-5.
- **Health exemption test included:** `test_health_endpoint_exempt` covers FR-4.
- **Window reset test included:** `test_window_reset_allows_new_requests` covers the window-expiry path of FR-1.
- **Identity isolation test included:** `test_different_identities_tracked_separately` covers FR-2.
- **All PRD open questions resolved** in §4 of architecture doc.

---

### 🟠 Gap 1 — Test isolation: `conftest.py` must be updated (architecture doc contradicts itself)

**Severity: Medium — must be reflected in story acceptance criteria**

Architecture §5 states:
> "No changes to existing test fixtures — `client` fixture in `conftest.py` works as-is"

This is incorrect, and the same section immediately contradicts itself:
> "`_store` must be cleared between tests (handled by `reset_rate_limiter` fixture above)"

The `autouse` fixture in `test_rate_limit.py` clears `_store` between tests **within that file only**. Tests in `test_orders.py` and `test_users.py` also fire requests that hit the rate limiter (they use the `client` fixture, which routes through the registered routers). Those requests accumulate entries in the module-level `_store` with no cleanup.

**Why this matters now:** Alphabetically, pytest runs `test_orders.py` before `test_rate_limit.py`. The orders tests fire ~10–12 requests (all keyed `ip:testclient`). With `MAX_REQUESTS=60`, no failure today. But:
- The architecture doc says no changes to `conftest.py` — which is wrong, and a story author following that instruction will leave a latent fragility
- If anyone lowers `RATE_LIMIT_REQUESTS` or adds more tests to existing files, this breaks silently

**Fix required in story:** Add `_store` reset to the `client` fixture teardown in `conftest.py`:

```python
# conftest.py — add to client fixture
import api.rate_limit as rl

@pytest.fixture
def client(db_engine):
    # ... existing setup ...
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    rl._store.clear()   # ← add this line
```

This is a one-line addition. The story's acceptance criteria must include: *"Existing tests (`test_users.py`, `test_orders.py`, `test_dates.py`) continue to pass without modification to their own files."*

---

### 🟡 Gap 2 — Dependency ordering claim in AD-3 is imprecise (minor — does not affect implementation)

**Severity: Minor — clarification only, no code change needed**

AD-3 states:
> "dependencies resolve in declaration order; router-level runs first"

FastAPI does not guarantee execution order between router-level and route-level dependencies when they have no shared sub-dependencies. `check_rate_limit(request: Request)` and `get_current_user(x_user_id, db)` share no sub-dependencies, so FastAPI may resolve them in any order.

**Why it doesn't matter:** The conclusion in AD-3 is correct regardless of ordering. If `get_current_user` fires first and returns `401`, the caller is rejected before any rate limit counter matters. If the rate limiter fires first, it keys on IP (no `X-User-Id` present) and increments — still correct behaviour.

**Recommendation for story author:** Do not add any code that relies on ordering between `check_rate_limit` and `get_current_user`. The implementation code as written in the architecture doc does not rely on this ordering, so no code change is needed. This note exists to prevent a future developer from adding ordering-dependent logic based on a misreading of AD-3.

---

### Non-issue — TestClient `request.client` host

The implementation handles `request.client is None` with fallback to `"unknown"`. FastAPI's `TestClient` (via Starlette/httpx) sets `request.client` to `("testclient", 50000)`, so `request.client.host` will be `"testclient"` in tests. All existing tests using the `client` fixture will share the key `ip:testclient`. This is expected and handled correctly once Gap 1's `conftest.py` fix is in place.

---

## Step 6 — Final Assessment

### Overall Readiness Status: **READY** *(one story, one `conftest.py` fix)*

### Issues Summary

| # | Severity | Description | Blocking? |
|---|---|---|---|
| Gap 1 | 🟠 Medium | `conftest.py` must reset `_store` in `client` fixture teardown | Must be in story AC |
| Gap 2 | 🟡 Minor | AD-3 misstates FastAPI dependency ordering; conclusion is still correct | Clarification only |

### Required Story Acceptance Criteria Additions

The story in §6 of the architecture doc should be augmented with:

1. "`conftest.py` updated: `rl._store.clear()` added to `client` fixture teardown after `app.dependency_overrides.clear()`"
2. "All pre-existing tests (`test_users.py`, `test_orders.py`, `test_dates.py`) pass without modification"
3. "`pytest` passes in its entirety (not just `test_rate_limit.py`)"

### Recommended Next Steps

1. **Story author:** Incorporate Gap 1 fix into the story spec — add `conftest.py` as a 5th file in scope
2. **Story author:** Note Gap 2 clarification in the story so no ordering-dependent logic is introduced
3. **Proceed to story creation** — the PRD and architecture are otherwise complete and traceable end-to-end

### Final Note

This assessment found **2 issues** across **2 categories**. Gap 1 is the only substantive one and requires a one-line addition to `conftest.py`. Gap 2 is a documentation precision issue with no code impact. Both can be addressed within the story without returning to the architect.
