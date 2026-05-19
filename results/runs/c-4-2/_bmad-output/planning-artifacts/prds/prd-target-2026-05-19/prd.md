---
title: Percentage Discount Codes at Checkout
status: draft
created: 2026-05-19
updated: 2026-05-19
---

# PRD: Percentage Discount Codes at Checkout

## 0. Document Purpose

This PRD is for the engineering team implementing the feature, the architect designing the data and API changes, and downstream workflow owners (epics, stories). It describes adding discount-code support to the existing order-creation flow in the `target` FastAPI service. The service already handles users, orders, and order items; this feature adds a `DiscountCode` concept and threads it through order creation. All monetary values in this service are stored as integer cents.

---

## 1. Vision

Merchants running the `target` service need a lightweight promotional lever. A percentage-discount code lets them hand a buyer a short string that, when submitted at order creation, reduces the order total by a fixed percentage. The experience is a single additional field on an existing API call — no new screens, no new auth — and the discount is persisted alongside the order for audit and display.

---

## 2. Target User

### 2.1 Primary Persona

**The API consumer / buyer** — a client (mobile app, web front-end, or integration partner) submitting an order on behalf of a user who holds a discount code. The user obtained the code through a promotional channel outside this service.

### 2.2 Jobs To Be Done

- Apply a discount I already have without leaving the checkout flow.
- Know immediately if my code is invalid or expired so I can proceed without it.
- Trust that the discounted total I see is the total that gets charged.

### 2.3 Non-Users (v1)

- Admins creating or managing discount codes via API — code management is seeded via fixtures/scripts only in v1.
- Analytics consumers querying discount redemption — out of scope.

### 2.4 Key User Journeys

**UJ-1. Buyer applies a valid discount code at checkout.**
- **Persona + context:** A buyer who received a 10%-off code via email submits an order through a client app.
- **Entry state:** Authenticated via `X-User-Id` header; has a non-empty cart.
- **Path:** (1) Client adds `"discount_code": "SAVE10"` to the `POST /orders` payload alongside items. (2) Service validates the code exists and is active. (3) Service computes the pre-discount total, applies the 10% reduction, and rounds to the nearest cent. (4) Order is persisted with both the pre-discount total and the discounted total, plus a reference to the code used.
- **Climax:** Response includes `discount_code`, `original_total`, and `total` (post-discount). The buyer sees exactly what was saved.
- **Resolution:** Order created; discount code marked used (if single-use) or usage count incremented.
- **Edge case:** Code has already been fully redeemed → 400 with `"discount code has been fully redeemed"`.

**UJ-2. Buyer submits an order without a discount code.**
- Existing behavior unchanged. `discount_code` is optional; omitting it produces the current response shape plus `discount_code: null` and `original_total == total`.

**UJ-3. Buyer submits an invalid or unknown code.**
- Service returns HTTP 400 with a clear error message. Order is not created.

---

## 3. Glossary

- **Discount Code** — A short alphanumeric string that maps to a fixed discount percentage (5, 10, or 20). Stored in the `discount_codes` table.
- **Discount Percentage** — One of the three allowed values: 5, 10, 20. Stored as an integer.
- **Original Total** — The sum of `unit_price × quantity` for all items before any discount, in integer cents.
- **Discounted Total** — `floor(original_total × (1 − discount_percentage / 100))`, in integer cents. This is what `Order.total` stores when a code is applied.
- **Checkout** — The act of calling `POST /orders`; no separate checkout endpoint exists.
- **Active** — A discount code whose `is_active` flag is `true` and whose usage has not exceeded its `max_uses` limit (if any).
- **Single-use Code** — A Discount Code with `max_uses = 1`.
- **Multi-use Code** — A Discount Code with `max_uses > 1` or `max_uses = null` (unlimited).

---

## 4. Features

### 4.1 Discount Code Catalog

**Description:** A new `DiscountCode` model persisted in SQLite holds each code's string, its percentage, and its redemption constraints. Codes are seeded via scripts or test fixtures; there is no management API in v1. The catalog is the source of truth for code validity.

**Functional Requirements:**

#### FR-1: DiscountCode model

The system stores a Discount Code record with: `code` (unique string, case-insensitive lookup), `percentage` (integer, one of 5 / 10 / 20), `is_active` (boolean, default true), `max_uses` (nullable integer — null means unlimited), `times_used` (integer, default 0).

**Consequences (testable):**
- A code with `is_active = false` is rejected at checkout even if `times_used < max_uses`.
- A code with `times_used >= max_uses` (when `max_uses` is not null) is rejected at checkout.
- Two codes differing only by case (`SAVE10` vs `save10`) resolve to the same record. [ASSUMPTION: case-folding to uppercase at lookup; confirm with team.]

**Out of Scope:**
- CRUD API endpoints for discount codes in v1.
- Expiry dates in v1.

---

### 4.2 Discount Application at Checkout

**Description:** The `POST /orders` endpoint accepts an optional `discount_code` string. When present, the service validates and applies it before persisting the order. The response is extended to surface discount details. Realizes UJ-1, UJ-2, UJ-3.

**Functional Requirements:**

#### FR-2: Optional discount_code field on order creation

`OrderCreate` accepts an optional `discount_code: str | None` field. Omitting it or passing `null` creates the order with no discount (existing behavior).

**Consequences (testable):**
- A request without `discount_code` returns the same shape as today, plus `discount_code: null` and `original_total == total`.
- A request with `discount_code: null` behaves identically to omitting the field.

#### FR-3: Discount code validation

When `discount_code` is provided, the service looks up the code (case-insensitive). If the code does not exist, is inactive, or is exhausted, it returns HTTP 400 with a descriptive `detail` message. The order is not persisted on validation failure.

**Consequences (testable):**
- Unknown code → 400, `"discount code not found"`.
- `is_active = false` code → 400, `"discount code is not active"`.
- `times_used >= max_uses` (non-null) → 400, `"discount code has been fully redeemed"`.
- Valid code → order proceeds to FR-4.

#### FR-4: Discount calculation and persistence

When a valid code is found, the service: (1) computes `original_total` as the sum of all line totals in cents; (2) computes `discounted_total = floor(original_total × (100 − percentage) / 100)`; (3) stores `Order.total = discounted_total`; (4) stores `Order.discount_code` (the code string) and `Order.discount_percentage` on the Order row; (5) increments `DiscountCode.times_used` atomically within the same transaction.

**Consequences (testable):**
- 10% discount on a $100.00 order → `total = 9000` cents, `original_total = 10000` cents.
- 5% discount on a $10.01 order → `original_total = 1001`, `discounted_total = floor(1001 × 0.95) = floor(950.95) = 950` cents.
- `times_used` increments by 1 after a successful checkout.
- If the DB write fails after code validation, `times_used` is not incremented (transactional).

#### FR-5: Extended order response

`OrderOut` is extended with: `discount_code: str | None`, `discount_percentage: int | None`, `original_total: int`. When no discount is applied, `discount_code` and `discount_percentage` are `null` and `original_total == total`.

**Consequences (testable):**
- Discounted order response contains all three new fields with correct values.
- Non-discounted order response has `discount_code: null`, `discount_percentage: null`, `original_total == total`.
- `GET /orders/{id}` returns the same extended shape (reads persisted fields).

---

### 4.3 Test Coverage

**Description:** All new behaviour is covered by pytest tests using the existing `client` fixture and in-memory SQLite. No new test infrastructure is needed.

**Functional Requirements:**

#### FR-6: Unit / integration tests

Tests cover: valid code applied (correct total, correct response fields, `times_used` incremented), no code supplied (backward compat), unknown code (400), inactive code (400), exhausted single-use code (400), rounding edge cases (fractional cents truncated), `GET /orders/{id}` returns discount fields.

**Consequences (testable):**
- `pytest` passes with zero failures.
- Each of the scenarios listed above has at least one dedicated test function.

---

## 5. Non-Goals (Explicit)

- **No discount code management API in v1.** Codes are seeded via scripts or test fixtures only.
- **No stacking of multiple codes.** One code per order maximum.
- **No flat-amount (dollar-off) discounts.** Percentage only.
- **No per-user or per-SKU restrictions.** A valid code applies to any order by any user.
- **No expiry dates.** Active/inactive flag is the only lifecycle control in v1.
- **No front-end or UI changes.** This is a pure API change.
- **No analytics or reporting endpoints** for discount redemption.
- **No admin auth.** Code management remains out-of-band.

---

## 6. MVP Scope

### 6.1 In Scope

- `DiscountCode` SQLAlchemy model (`discount_codes` table).
- `Order` model extended with `discount_code`, `discount_percentage`, `original_total` columns. [ASSUMPTION: `original_total` stored on the order row rather than computed; confirm with architect — storing it avoids recomputation and is consistent with the cents-storage pattern.]
- `POST /orders` extended with optional `discount_code` input, validation logic, discount math, and extended response.
- `GET /orders/{id}` extended response (reads persisted fields, no new logic).
- pytest tests covering all FR-6 scenarios.

### 6.2 Out of Scope for MVP

- All items listed in §5 Non-Goals.
- Schema migrations (operator wipes `app.db` between runs per CLAUDE.md).

---

## 7. Success Metrics

- Zero test failures in `pytest` after implementation.
- `POST /orders` with a valid discount code returns `total < original_total` equal to the correct discounted amount.
- Backward compatibility: existing `POST /orders` callers (no `discount_code` field) see no change in response shape beyond the three new nullable/equal fields.

**Counter-metric:** If `total == original_total` when a discount code was supplied, the discount was silently dropped — this must not happen.

---

## 8. Open Questions

| # | Question | Owner | Revisit condition |
|---|----------|-------|-------------------|
| OQ-1 | Should a single-use code be locked/reserved at validation time to prevent race conditions on concurrent checkouts, or is last-write-wins acceptable for v1 given SQLite's serialized writes? | Architect | Before implementation begins |
| OQ-2 | Should `original_total` be a persisted column on `orders`, or computed on the fly in the response? Storing it is consistent with the cents pattern and enables future auditing. | Architect | Architecture decision |
| OQ-3 | Case sensitivity: fold to uppercase at insert and lookup, or store and compare as-is? Affects seeding scripts. | Engineer | Before seeding fixtures are written |
| OQ-4 | Should `GET /orders/{id}` gate on ownership (current behavior) or allow admins to read any order? No change proposed for v1, but discount fields will be visible — confirm this is acceptable. | PM / stakeholder | Before shipping |
| OQ-5 | Is `max_uses = null` (unlimited uses) a required v1 capability, or should all codes be single-use to simplify the model? | PM | Before DB schema is finalised |
