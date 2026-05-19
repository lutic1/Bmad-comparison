---
title: Percentage Discount Codes at Checkout
status: draft
created: 2026-05-18
updated: 2026-05-18
---

# PRD: Percentage Discount Codes at Checkout

## 0. Document Purpose

This PRD is for the engineering team implementing the discount-code feature on the `target` FastAPI service. It defines functional requirements, explicit non-goals, acceptance criteria, and open questions. Downstream: architecture and story breakdown.

---

## 1. Vision

Users placing orders can supply a short alphanumeric discount code that reduces their order total by a fixed percentage (5 %, 10 %, or 20 %). The feature adds a `DiscountCode` table to the existing SQLite schema, extends the `POST /orders` endpoint to accept and validate the code, and adjusts the computed total before persisting the order. Tests ship alongside the implementation.

---

## 2. Target User

**Primary persona:** Any authenticated API consumer (identified via `X-User-Id` header) who holds a valid discount code.

**Jobs to be done:**
- Apply a code I received and see a lower total on my order confirmation.
- Trust that an invalid or non-existent code is rejected clearly, not silently ignored.

**UJ-1. User applies a valid discount at order creation.**
> Authenticated user POSTs to `/orders` with `items` and `discount_code: "SAVE10"`. The service looks up the code, finds it maps to 10 %, recomputes `total = sum(items) × 0.90`, stores the order with `discount_code` and `discount_pct` recorded, and returns the discounted total in the response.

**UJ-2. User submits an unknown or invalid code.**
> User POSTs with `discount_code: "BOGUS"`. Service returns HTTP 422 with a clear error message. No order is created.

---

## 3. Glossary

- **Discount Code** — A short string (e.g. `"SAVE10"`) stored in the `discount_codes` table that maps to one of the allowed percentages (5, 10, 20).
- **Discount Percentage** — The integer percentage off the order total: one of `{5, 10, 20}`.
- **Order Total** — The sum of `unit_price × quantity` for all items in the order, expressed in cents, **after** any discount is applied.
- **Original Total** — The pre-discount sum of line items, also in cents.
- **Checkout** — The act of calling `POST /orders`; there is no separate checkout step.

---

## 4. Features

### 4.1 Discount Code Catalogue

**Description:** A new `discount_codes` table holds all valid codes and their associated percentage. Codes are pre-seeded by the operator; there is no admin API to create them in v1. [ASSUMPTION: codes are case-insensitive on lookup.]

**Functional Requirements:**

#### FR-1: Discount code storage

The system stores discount codes in a `discount_codes` table with at minimum: `code` (unique string), `percentage` (integer, one of 5 / 10 / 20).

**Consequences (testable):**
- A code inserted into `discount_codes` can be retrieved by exact string match (case-insensitive).
- `percentage` values outside `{5, 10, 20}` are rejected at the DB or model layer.

---

### 4.2 Apply Discount at Checkout

**Description:** `POST /orders` gains an optional `discount_code` field. When provided, the service validates the code against `discount_codes`, computes the discounted total, and records both the code string and percentage on the order. Realizes UJ-1 and UJ-2.

**Functional Requirements:**

#### FR-2: Optional discount_code field on order creation

A caller may include `discount_code: str` (optional, nullable) in the `POST /orders` request body.

**Consequences (testable):**
- Omitting `discount_code` (or passing `null`) creates the order at full price — existing behaviour is unchanged.
- Including a valid code creates the order with `total = round(original_total × (1 − pct/100))`.

#### FR-3: Discount code validation

When `discount_code` is supplied, the service looks it up in `discount_codes` (case-insensitive). If not found, the request is rejected before any order is persisted.

**Consequences (testable):**
- Unknown code → HTTP 422 with a human-readable error body referencing the invalid code.
- Valid code → order created; HTTP 201 with discounted `total` in response.

#### FR-4: Discount metadata on order

The persisted `Order` record stores the applied `discount_code` (string) and `discount_pct` (integer). Both are `null` when no code was used.

**Consequences (testable):**
- Fetching the order after creation returns `discount_code` and `discount_pct` in the response body.
- Orders created without a code return `discount_code: null` and `discount_pct: null`.

#### FR-5: Discounted total in response

The `OrderOut` response schema includes the discounted `total`, and — when a discount was applied — `discount_code` and `discount_pct`.

**Consequences (testable):**
- `total` in the response equals `round(sum(unit_price × qty) × (1 − pct/100))`.
- Response includes `discount_code` and `discount_pct` fields (null-able).

---

## 5. Non-Goals (Explicit)

- **No admin API for code management.** Codes are seeded directly; CRUD endpoints are out of scope.
- **No single-use or per-user-use limits.** The same code may be applied to any number of orders.
- **No stacking.** Only one discount code per order.
- **No expiry or date-range logic.** Codes are active until manually removed from the DB.
- **No dollar-amount or free-shipping discounts.** Percentages only, fixed set `{5, 10, 20}`.
- **No discount on individual line items.** Discount applies to the order total only.
- **No UI.** This is an API-only service.

---

## 6. MVP Scope

### 6.1 In Scope

- `discount_codes` table (SQLAlchemy model, auto-created from `Base.metadata`).
- `DiscountCode` seed data for at least the three canonical percentages.
- `Order.discount_code` and `Order.discount_pct` nullable columns.
- `POST /orders` accepting optional `discount_code`, validating, computing discounted total.
- Updated `OrderCreate` (request) and `OrderOut` (response) Pydantic schemas.
- pytest coverage: valid code, unknown code, no code (regression), each discount tier.

### 6.2 Out of Scope for MVP

- Admin endpoints to create/update/delete codes.
- Per-user or per-order usage tracking.
- Code expiry.
- Async DB driver (not used today).

---

## 7. Success Metrics

**Primary**
- **SM-1:** `POST /orders` with a valid discount code returns HTTP 201 with a correctly discounted total in 100 % of test cases. Validates FR-2, FR-3, FR-5.

**Secondary**
- **SM-2:** `POST /orders` with an invalid code returns HTTP 422 and creates zero order records. Validates FR-3.
- **SM-3:** `POST /orders` without a code behaves identically to today (no regression). Validates FR-2.

**Counter-metrics (do not optimise)**
- **SM-C1:** Discount percentage must not be inferred from the code string; it must always be looked up from `discount_codes`. Prevents logic drift if code-naming conventions change.

---

## 8. Open Questions

1. **Case sensitivity.** Should `"save10"` match `"SAVE10"`? [ASSUMPTION: yes, case-insensitive] — confirm before implementation.
2. **Seed mechanism.** Should the app seed canonical codes on startup (e.g. `SAVE5`, `SAVE10`, `SAVE20`), or does the operator insert them manually? Affects conftest setup and production runbook.
3. **Rounding rule.** When `total × (1 − pct/100)` is not a whole number of cents, should we floor, ceil, or round-half-up? [ASSUMPTION: standard `round()`] — confirm to avoid test flakiness.
4. **Error code.** Should an invalid discount code return HTTP 422 (validation) or HTTP 400 (bad request)? 422 is consistent with FastAPI's default validation errors.
5. **Response schema backward compatibility.** Adding `discount_code` and `discount_pct` to `OrderOut` is additive; existing consumers should be unaffected. Confirm no consumer treats the response as a closed schema.

---

## 9. Assumptions Index

- **§3 / FR-3:** Discount code lookup is case-insensitive.
- **§8 / OQ-3:** Discounted total is computed with standard `round()` (half-up in Python 3).
- **§5:** A code may be reused across multiple orders without restriction.
- **§4.1:** Codes are pre-seeded; no runtime creation API is needed for v1.
