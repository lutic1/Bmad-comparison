# Data Model: Discount Codes at Checkout

## New Entity: DiscountCode

| Column       | Type         | Constraints                    | Notes                          |
|--------------|--------------|--------------------------------|--------------------------------|
| `id`         | Integer      | PK, autoincrement              |                                |
| `code`       | String       | NOT NULL, UNIQUE               | Stored uppercase (e.g. SAVE10) |
| `percentage` | Integer      | NOT NULL, CHECK (IN 5, 10, 20) | Applied discount percentage    |

**Seeded rows** (inserted at startup, idempotent):

| code    | percentage |
|---------|------------|
| SAVE5   | 5          |
| SAVE10  | 10         |
| SAVE20  | 20         |

---

## Modified Entity: Order

New nullable column added:

| Column          | Type    | Constraints | Notes                                    |
|-----------------|---------|-------------|------------------------------------------|
| `discount_code` | String  | NULL allowed | Applied code (uppercase); NULL if none  |

**Existing columns unchanged**: `id`, `user_id`, `total`, `created_at`,
`items` relationship.

`total` continues to store the **final amount in cents** (post-discount).
No gross/net split is stored; the pre-discount total is derivable from
`sum(item.unit_price * item.quantity)` if ever needed.

---

## Relationships

```
DiscountCode (standalone lookup table)
  code ───────────────────────────────► Order.discount_code (denormalised copy)
  No FK enforced — code string is copied at order-creation time so historical
  orders are unaffected if a code is later removed.
```

---

## Validation Rules

- `DiscountCode.percentage` MUST be one of `{5, 10, 20}` (enforced in seed
  data and route handler; no DB CHECK constraint required in SQLite).
- `Order.discount_code` is the uppercase form of whatever the user submitted.
- Discount calculation: `discount_cents = round(gross_total * percentage / 100)`
- Post-discount total: `final_total = gross_total - discount_cents` (minimum 0).
