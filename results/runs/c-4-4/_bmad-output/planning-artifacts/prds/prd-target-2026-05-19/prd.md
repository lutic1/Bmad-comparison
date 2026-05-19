---
title: Percentage Discount Codes at Checkout
status: draft
created: 2026-05-19
updated: 2026-05-19
---

# PRD: Percentage Discount Codes at Checkout

## 0. Document Purpose

This PRD specifies a small feature for the existing FastAPI users/orders service:
the ability for a user to apply a percentage discount code when creating an
order. It is scoped to a single feature, deliberately tight, and intended as
direct input to the architect and the developer. Downstream readers should
treat the four headline sections (Goals, Non-Goals, Acceptance Criteria, Open
Questions) as load-bearing; everything else is supporting context.

## 1. Vision

Customers placing an order through `POST /orders` should be able to redeem a
short, human-typed code (e.g. `SAVE10`) that knocks a fixed percentage off the
order total. The service supports exactly three discount tiers — 5%, 10%, and
20% — and stores the resulting order at the discounted total. The change is
small in surface area but materially changes a money-bearing endpoint, so the
behaviour around rounding, validation, and persistence has to be unambiguous.

## 2. Goals

1. Let a caller pass a discount code on order creation and have the order
   total reduced by the corresponding percentage (5%, 10%, or 20%).
2. Persist the discount applied to each order so it is recoverable on
   `GET /orders/{id}` and auditable later.
3. Reject invalid, unknown, or malformed codes with a clear 4xx response and
   leave no order written.
4. Ship behind regression tests that cover the happy path, each tier, the
   rejection path, and the rounding boundary.
5. Preserve the existing money-in-cents invariant — the stored `total` remains
   an integer number of cents.

## 3. Non-Goals

- **No code management UI or admin API.** The three codes are configured
  in-code (or in a small constant table) for v1. No create/list/revoke
  endpoints.
- **No per-user or per-order usage limits.** A code can be redeemed
  arbitrarily many times by the same or different users in v1.
- **No expiry / start dates / scheduling.** Codes are either active or
  removed from the constant; there is no time window logic.
- **No stacking.** At most one code per order. Multiple codes is out of scope.
- **No fixed-amount discounts, free-shipping codes, BOGO, or category-scoped
  discounts.** Percentage-off whole order only.
- **No minimum order value / maximum discount cap.** v1 applies the percentage
  unconditionally to whatever the order total is.
- **No refund / partial-refund recalculation.** Refund flow does not exist in
  the service today and is not being added.
- **No analytics, metrics, or logging beyond what the rest of the service
  already does.** (Per `CLAUDE.md`.)
- **No new third-party dependencies.** Stdlib + existing stack only.
- **No migrations.** Schema is rebuilt from `Base.metadata` between runs
  per the project's stated convention; new columns are added directly to the
  model.

## 4. Feature

### 4.1 Apply discount code on order creation

**Description.** `POST /orders` accepts an optional `discount_code` field on
the request body. When present and recognized, the server computes a
discounted total, persists the order at that total, and records which code
was applied and what percentage it represented. When present and not
recognized (or otherwise invalid), the server returns `400` and writes no
order. When absent, behaviour is identical to today.

**Functional Requirements**

#### FR-1: Accept an optional discount code on order creation
A caller can include `discount_code: string | null` on the `POST /orders`
body. Omitting the field, or sending `null`, behaves exactly as the current
endpoint does today.

**Consequences (testable):**
- Existing tests in `tests/test_orders.py` continue to pass without change.
- A request body with no `discount_code` field returns the same `OrderOut`
  shape and `total` as before the change.

#### FR-2: Recognize the three valid codes
The service recognizes exactly three codes mapped to fixed percentages.
Codes are case-insensitive on input but stored canonical-cased.

**Consequences (testable):**
- `SAVE5` → 5%, `SAVE10` → 10%, `SAVE20` → 20% are accepted.
  *[ASSUMPTION: literal code strings — confirm with stakeholder before
  freezing user-visible strings.]*
- Lower- and mixed-case variants (`save10`, `Save10`) are accepted and
  treated identically to the canonical form.
- The mapping lives in a single module-level constant; adding or removing
  a tier is a one-line code change.

#### FR-3: Compute and persist the discounted total
For a valid code, the stored `Order.total` equals
`round_half_even(subtotal_cents * (100 - percent) / 100)`, where
`subtotal_cents` is the same sum-of-line-items the endpoint computes today.

**Consequences (testable):**
- For a subtotal of `1000` cents and code `SAVE10`, stored `total` is `900`.
- For a subtotal of `999` cents and code `SAVE10`, stored `total` is `899`
  (banker's rounding: `899.1` → `899`).
  *[ASSUMPTION: banker's rounding (Python `round` default) is acceptable.
  Confirm if half-up is required for finance/legal reasons — see Open
  Question 1.]*
- `total` remains a non-negative integer number of cents.
- Line item `unit_price` values are stored unchanged — the discount is
  applied at the order level, not per line.

#### FR-4: Reject unknown or malformed codes
Any non-null `discount_code` that does not match a recognized entry (after
case-folding) causes a `400 Bad Request` with body
`{"detail": "invalid discount code"}`. No order, and no order items, are
written.

**Consequences (testable):**
- `discount_code: "NOPE"` → 400, no row inserted into `orders` or
  `order_items`.
- `discount_code: ""` (empty string) → 400.
  *[ASSUMPTION: empty string is treated as invalid rather than as "no
  code". Confirm — see Open Question 2.]*
- `discount_code: "   SAVE10  "` is accepted (leading/trailing whitespace
  trimmed). *[ASSUMPTION — confirm with stakeholder.]*

#### FR-5: Expose the applied discount on the order
`GET /orders/{id}` and the `POST /orders` response surface which code (if
any) was applied and the resulting percentage, so a caller can render
"You saved 10%".

**Consequences (testable):**
- `OrderOut` includes two new fields: `discount_code: string | null` and
  `discount_percent: int | null`. Both are `null` when no code was applied.
- A round-trip (create then get) returns the same `discount_code` and
  `discount_percent` originally supplied.

## 5. Acceptance Criteria

The feature is accepted when **all** of the following are true and ship
with regression tests in `tests/`:

- **AC-1 (no code, unchanged behaviour):** `POST /orders` without a
  `discount_code` field returns the same shape and `total` as today.
  Existing `test_orders.py` tests pass unmodified.
- **AC-2 (each tier applies correctly):** for a known subtotal, applying
  `SAVE5`, `SAVE10`, and `SAVE20` each produces the expected discounted
  `total` in cents. One test per tier.
- **AC-3 (rounding boundary):** a subtotal chosen to force a fractional
  cent (e.g. `999 * SAVE10`) rounds per FR-3 and stores an integer
  `total`. Test asserts the exact integer.
- **AC-4 (case-insensitive input):** `save10` and `Save10` produce the
  same result as `SAVE10`.
- **AC-5 (invalid code rejected, no side effects):** an unknown code
  returns `400` and the database contains zero new orders and zero new
  order items afterwards.
- **AC-6 (read path exposes discount):** `GET /orders/{id}` for an order
  created with `SAVE20` returns `discount_code: "SAVE20"` and
  `discount_percent: 20`. For an order created with no code, both fields
  are `null`.
- **AC-7 (auth boundary preserved):** the existing `X-User-Id` /
  `get_current_user` rules still gate the endpoint; a missing or invalid
  header behaves exactly as today.
- **AC-8 (cents invariant):** stored `Order.total` is always a
  non-negative integer for every test above.
- **AC-9 (`pytest` is green):** the full test suite passes. Per
  `CLAUDE.md`, the change does not ship if `pytest` is failing.

## 6. Open Questions

1. **Rounding policy.** FR-3 uses banker's rounding (Python's built-in
   `round`). Most retail finance uses half-up. Which is required?
   Decision needed before architect freezes the math helper.
2. **Empty string handling.** Should `discount_code: ""` be treated as
   "no code applied" (current `null` semantics) or as an invalid code
   (current FR-4 assumption)? The latter is stricter and surfaces typos.
3. **Code strings.** Are `SAVE5` / `SAVE10` / `SAVE20` the actual codes
   marketing wants, or placeholders? Codes are user-visible.
4. **Future stacking / per-user limits.** Non-goals today, but if v2 is
   already planned the architect may want to leave room in the schema
   (e.g. discount lives on a row with a foreign key rather than two
   columns on `orders`). Worth a 30-second conversation.
5. **Auditability.** Should we persist the *cents* discount amount
   (`discount_cents`) alongside the percent, so historical reporting
   doesn't have to recompute against possibly-changed mappings? Cheap
   to add now, expensive to backfill later.

## 7. Assumptions Index

- FR-2: code strings `SAVE5` / `SAVE10` / `SAVE20` are placeholders pending
  marketing confirmation (Open Question 3).
- FR-3: banker's rounding via Python `round` is acceptable (Open Question 1).
- FR-4: empty string is invalid, not equivalent to omission (Open Question 2).
- FR-4: leading/trailing whitespace is trimmed before lookup.
- Section 3: no admin endpoint, no expiry, no stacking, no caps — v1 ships
  with the three codes hard-coded in a constant.

---

ready for architect handoff
