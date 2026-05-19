## Deferred from: code review of 1-1/1-2 discount-codes (2026-05-19)

- **Date format `%Y-%d-%m` in order responses** — `src/api/routes/orders.py` lines 107, 134. Day and month are swapped vs ISO 8601. Pre-existing convention across the codebase; not introduced by this change. Fix requires coordinating with all API consumers.
- **`DiscountCode.percentage` has no DB-level min/max constraint** — `src/api/models.py`. Accepts any integer; a value outside 0–100 would produce incorrect totals. No management API in v1 so risk is limited to operator seeding error. Revisit if a management API is added.
- **`OrderItem.quantity` accepts negative values** — `src/api/models.py`. Pre-existing; not introduced by discount feature. Negative quantities reduce order total and could produce free orders. Fix: add `quantity > 0` validator to `OrderItemIn`.
