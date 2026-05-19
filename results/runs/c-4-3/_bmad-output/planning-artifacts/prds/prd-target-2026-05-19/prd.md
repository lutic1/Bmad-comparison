---
title: Discount Code at Checkout
status: final
created: 2026-05-19
updated: 2026-05-19
---

# PRD: Discount Code at Checkout

## 0. Document Purpose

This PRD is for the development team implementing a percentage discount code feature on the existing `target` FastAPI service (users + orders, SQLite). It defines requirements for the PM, engineer, and any downstream reviewer. The service already computes order totals in integer cents; this feature adds a new `DiscountCode` entity and wires it into order creation.

---

## 1. Vision

Customers placing orders should be able to apply a pre-configured discount code that reduces their order total by a fixed percentage (5 %, 10 %, or 20 %). The feature is narrow by design: no dynamic creation of codes by end-users, no stacking, no expiry in v1. It adds one database table, one optional field on the order-creation request, and one new field on the order response.

---

## 2. Target User

### 2.1 Primary Persona

An API consumer (front-end client or integration partner) that submits orders on behalf of authenticated users. They obtain a discount code through an out-of-band channel (marketing campaign, manual provisioning) and pass it at order creation.

### 2.2 Jobs To Be Done

- Apply a valid discount code at order creation and see the reduced total reflected immediately.
- Receive a clear error when a code is unknown or already exhausted (if single-use) — so the caller can surface it to the end-user.

### 2.3 Non-Users (v1)

- End-users who want to *create* or *manage* discount codes — that is an admin-only, out-of-scope operation seeded directly in the database.
- Callers expecting to stack multiple codes on one order.

---

## 3. Glossary

- **DiscountCode** — A database record with a unique string `code`, a `percentage` (one of 5, 10, 20), and an optional `single_use` flag. Managed out-of-band by operators.
- **Order** — An existing entity representing a placed order. Has a `total` (integer cents) and, after this feature, an optional `discount_code` and `discounted_total` (integer cents).
- **Original Total** — Sum of `unit_price_cents × quantity` across all `OrderItem` rows; computed before any discount.
- **Discounted Total** — `round(original_total × (1 − percentage / 100))`, in cents. Stored alongside the original total.
- **Checkout** — The act of submitting `POST /orders`; the only point at which a discount code may be applied.

---

## 4. Features

### 4.1 Discount Code Application at Order Creation

**Description:** When `POST /orders` receives an optional `discount_code` string, the system looks up the corresponding `DiscountCode`. If valid, it computes the `discounted_total` and stores it on the `Order`. If the code is unknown or exhausted, the request is rejected with a `422`. Orders with no code set behave exactly as today — no `discounted_total` field is populated (or it equals `total`). Realizes UJ-1.

**Functional Requirements:**

#### FR-1: Optional discount_code field on order creation

A caller MAY include `discount_code` (string) in the `POST /orders` request body. Omitting the field is equivalent to not applying a discount.

**Consequences (testable):**
- `POST /orders` without `discount_code` succeeds and behaves identically to the current implementation.
- `POST /orders` with `discount_code` present and valid completes with HTTP 201.
- `POST /orders` with `discount_code` present but unknown returns HTTP 422 with a descriptive error message.

#### FR-2: Discounted total computation

When a valid code is applied, the system computes `discounted_total = round(original_total × (1 − percentage / 100))` in integer cents and stores it on the `Order`.

**Consequences (testable):**
- A 10 % code on a 1000-cent order produces `discounted_total = 900`.
- A 5 % code on a 999-cent order produces `discounted_total = 949` (round(999 × 0.95) = round(949.05) = 949).
- A 20 % code on a 1001-cent order produces `discounted_total = 801` (round(1001 × 0.80) = round(800.8) = 801).
- `discounted_total` is never negative.

#### FR-3: Order response includes discount fields

`GET /orders/{id}` and the creation response include `discount_code` (string | null) and `discounted_total` (int | null) when a discount was applied; both fields are null/absent otherwise.

**Consequences (testable):**
- Response for an order with a code contains `discount_code` matching the applied code string and `discounted_total` equal to the computed value.
- Response for an order without a code has `discount_code: null` and `discounted_total: null` (or omits the fields — implementation choice, but consistent).

#### FR-4: DiscountCode database table

A new `discount_codes` table with columns: `id` (PK), `code` (unique string, required), `percentage` (integer, one of 5/10/20, required).

**Consequences (testable):**
- Inserting a `DiscountCode` with `percentage` outside {5, 10, 20} is rejected at the application layer (validation in the model or a check constraint).
- Two `DiscountCode` rows with the same `code` string cannot coexist.

**Feature-specific NFRs:**
- Lookup of a `DiscountCode` by `code` must use a database-level unique index so it is O(1) and safe under concurrent inserts.

---

## 5. Non-Goals

- **Admin API for code management.** Codes are seeded directly in the database or via fixtures. No `POST /discount-codes` endpoint in v1.
- **Code expiry / validity windows.** No `expires_at`, `valid_from`, or date-gating logic.
- **Single-use / redemption tracking.** Codes may be reused unlimited times in v1.
- **Stackable discounts.** One code per order, no combining.
- **Percentage values other than 5, 10, 20.** The allowed set is fixed.
- **Discount on individual line items.** Discount applies to the order total only.
- **User-facing code discovery.** No endpoint listing available codes.

---

## 6. MVP Scope

### 6.1 In Scope

- `discount_codes` table and `DiscountCode` SQLAlchemy model.
- `discount_code` optional field on `OrderCreate` Pydantic schema.
- Lookup, validation (unknown code → 422), and computation logic in `POST /orders`.
- `discount_code` and `discounted_total` fields on `OrderOut` response schema.
- `Order` model gains `discount_code` (nullable string) and `discounted_total` (nullable int) columns.
- pytest coverage: valid code (each of 5 %, 10 %, 20 %), unknown code, no code (regression).

### 6.2 Out of Scope for MVP

- Admin CRUD for discount codes — deferred to v2.
- Single-use / expiry logic — deferred to v2.
- Discount reflected in `GET /orders` list endpoint (only creation + detail in v1). [NOTE FOR PM: revisit before v2 if clients need list filtering by discounted orders]

---

## 7. Success Metrics

**Primary**
- **SM-1**: All new pytest cases pass; existing suite has zero regressions. Validates FR-1 through FR-4.

**Secondary**
- **SM-2**: `POST /orders` p99 latency does not increase by more than 5 ms (one extra indexed DB lookup). Validates FR-4 NFR.

**Counter-metrics (do not optimize)**
- **SM-C1**: Do not optimize for code reuse rate — the absence of single-use tracking is intentional for v1 simplicity, not a gap to patch.

---

## 8. Open Questions

1. **Code seeding mechanism.** How will operators insert `DiscountCode` rows in production — direct SQL, a fixture script, or a future admin endpoint? Answer needed before go-live, not before implementation.
2. **Rounding convention.** Python's `round()` uses banker's rounding (round-half-to-even). Is this acceptable, or should the service use `math.floor` / `math.ceil`? [ASSUMPTION: standard `round()` is acceptable — confirm with product owner.]
3. **`discounted_total` when no discount applied.** Should the field be omitted from the response, or present as `null`? Either is consistent; pick one and enforce it in tests. [ASSUMPTION: `null` is cleaner for clients; implementation should confirm.]
4. **Index vs. check constraint for percentage.** SQLite does not enforce `CHECK` constraints by default in older versions. Should validation live solely in the Pydantic model, or also in a SQLAlchemy `CheckConstraint`?

---

## 9. Assumptions Index

- **§4.1 / FR-2** — `round()` (banker's rounding) is the accepted rounding method.
- **§4.1 / FR-3** — Fields are `null` (not omitted) when no discount was applied; response schema is consistent across all orders.
- **§4.1 / FR-4** — Percentage validation is enforced at the application layer; a database `CHECK` constraint is optional / additive.
- **§6.1** — Codes are seeded manually; no admin API is needed for the initial deployment.
