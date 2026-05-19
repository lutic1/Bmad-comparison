# Data Model: Percentage Discount Codes at Checkout

## Changes to existing entities

### `Order` (table `orders`, `src/api/models.py`)

Add two nullable columns. Existing columns unchanged.

| Column          | Type            | Nullable | Default | Notes                                                              |
|-----------------|-----------------|----------|---------|--------------------------------------------------------------------|
| `subtotal`      | `Integer`       | yes      | `NULL`  | Pre-discount total in cents. Snapshotted on first discount apply.  |
| `discount_code` | `String(16)`    | yes      | `NULL`  | Uppercased canonical code (`SAVE5` / `SAVE10` / `SAVE20`).         |
| `total`         | `Integer`       | no       | —       | **Existing.** Now equals discounted total when a code is applied.  |

**Invariants**:

- If `discount_code IS NOT NULL` then `subtotal IS NOT NULL` and
  `subtotal >= total >= 0`.
- If `discount_code IS NULL` then `total` is the order's full subtotal
  (existing behaviour; `subtotal` may be `NULL` for orders that never
  had a discount applied).
- `discount_code`, when present, is always one of the three values
  defined in `DISCOUNT_CODES` (see contract).

**Validation rules** (enforced at the route layer):

- `code` from the request body MUST be a non-empty string.
- `code.upper()` MUST be a key of `DISCOUNT_CODES`; otherwise return
  HTTP 400.
- Only the owner of the order may apply a code (HTTP 403 otherwise),
  same rule as `GET /orders/{order_id}`.

**State transitions**:

```text
(no discount)            ──apply SAVE{n}──▶  (discount applied)
                                                │
                                                │ apply SAVE{m}
                                                ▼
                                          (discount applied,
                                           replacing previous)
```

Order confirmation is implicit in this service (an order is "confirmed"
the moment it exists). No explicit state column is added.

## New entities

None. The set of valid codes is a fixed in-code constant
(`DISCOUNT_CODES`), not a database table — see research.md Decision 1.

## Derived values

For an `Order` with `discount_code = code` and `subtotal = s_cents`:

```text
percentage     = DISCOUNT_CODES[code]                     # 5, 10, or 20
discount_cents = (s_cents * percentage + 50) // 100       # half-up
total_cents    = s_cents - discount_cents
```

When the discount endpoint is called for the first time on an order,
`subtotal` is initialised from the order's current `total` before the
new `total` is written.
