# Research: Discount Code at Checkout

**Feature**: 001-discount-codes
**Date**: 2026-05-18

## Summary

No external research was required. All technical decisions are fully
determined by the constitution (stack, testing, conventions) and the
existing codebase patterns.

---

## Decision Log

### Storage strategy for applied discount

**Decision**: Store `discount_code_id` as a nullable FK on `Order`;
keep `Order.total` as the original subtotal (pre-discount). Compute
`discount_amount` and `final_total` in the response schema.

**Rationale**: Preserves the original subtotal for auditability.
Avoids a second numeric field on `Order` that would duplicate
information derivable from `discount_code.percentage`. Consistent
with the existing pattern where `total` is computed from items at
creation time and stored; reading back a richer view is done in
the Pydantic response model.

**Alternatives considered**:
- Mutate `Order.total` in place (lose original subtotal, harder to
  reverse or audit).
- Add a separate `discount_amount` column to `Order` (redundant once
  the code's percentage is available via FK join).

---

### Endpoint placement

**Decision**: `POST /orders/{order_id}/apply-discount` on the existing
orders router.

**Rationale**: Discount application is an action on an existing order,
not a resource creation. A sub-resource action path under `/orders`
follows the REST convention used elsewhere in the service (e.g.,
`GET /orders/{order_id}`). No new router file is needed.

**Alternatives considered**:
- `PATCH /orders/{order_id}` — too generic; conflates discount
  application with other order mutations.
- Separate `/discounts` router — unnecessary indirection for a
  single endpoint.

---

### One-code-per-order enforcement

**Decision**: Check `Order.discount_code_id is not None` at the
start of the endpoint handler. Return HTTP 400 if already set.

**Rationale**: The nullable FK is the source of truth. No additional
flag or table needed. Consistent with how the existing codebase
returns 400 for empty item lists.

---

### Case normalisation

**Decision**: `code.strip().upper()` before DB lookup.

**Rationale**: FR-008 requires trimming whitespace and
case-insensitivity. Normalising to uppercase at the entry point
means codes are stored uppercase and lookups are O(1) index hits
rather than case-insensitive scans.

---

### No new third-party dependencies

**Decision**: All work done with existing stdlib + installed packages.

**Rationale**: Constitution V prohibits new dependencies without
justification. Nothing in this feature requires them.
