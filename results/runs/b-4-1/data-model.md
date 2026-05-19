# Data Model: Discount Code at Checkout

**Feature**: 001-discount-codes
**Date**: 2026-05-18

---

## New Entity: DiscountCode

**Table**: `discount_codes`

| Column       | Type         | Constraints                    | Notes                          |
|-------------|-------------|-------------------------------|-------------------------------|
| `id`        | Integer      | PK, auto-increment             |                                |
| `code`      | String(64)   | UNIQUE, NOT NULL               | Stored uppercase; e.g. SAVE10 |
| `percentage`| Integer      | NOT NULL, CHECK IN (5, 10, 20) | Discount tier                  |
| `is_active` | Boolean      | NOT NULL, DEFAULT TRUE         | Soft-disable without deletion  |

**Relationships**:
- One `DiscountCode` → many `Orders` (back-populated as `discount_code`
  on `Order`)

**Validation rules**:
- `percentage` MUST be one of 5, 10, 20.
- `code` is normalised to uppercase before insert and lookup.

---

## Modified Entity: Order

**Existing table**: `orders`

**New column**:

| Column             | Type    | Constraints                         | Notes                           |
|--------------------|---------|-------------------------------------|---------------------------------|
| `discount_code_id` | Integer | FK → `discount_codes.id`, NULLABLE  | NULL = no discount applied yet  |

**Existing `total` column**: remains as the original subtotal in cents,
computed from items at order creation. It is **not** modified when a
discount is applied; the discounted total is derived at read time.

**Relationships (addition)**:
- `Order.discount_code` → optional `DiscountCode` (many-to-one)

---

## Derived fields (Pydantic response only, not stored)

These fields appear in `OrderWithDiscountOut` and are computed from the
stored data:

| Field               | Formula                                    |
|--------------------|--------------------------------------------|
| `subtotal`          | `Order.total`                              |
| `discount_code`     | `DiscountCode.code` or `null`              |
| `discount_percentage` | `DiscountCode.percentage` or `null`      |
| `discount_amount`   | `round(subtotal * percentage / 100)`       |
| `final_total`       | `subtotal - discount_amount`               |

All monetary values are in **cents** (integer), consistent with the
existing service convention.

---

## Entity Relationship Diagram (text)

```
users (1) ──< orders (N)
                  │
                  └──> discount_codes (0..1)
orders (1) ──< order_items (N)
```
