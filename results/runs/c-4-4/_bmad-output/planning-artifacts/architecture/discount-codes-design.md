---
title: Technical Design — Percentage Discount Codes at Checkout
status: draft
created: 2026-05-19
updated: 2026-05-19
related_prd: ../prds/prd-target-2026-05-19/prd.md
---

# Technical Design — Percentage Discount Codes at Checkout

## 0. Scope

This document is the implementation-shaped companion to the PRD at
`../prds/prd-target-2026-05-19/prd.md`. It identifies which files change and
how, names the small set of decisions that the PRD left open, and stops
there. Story breakdown and test code live downstream.

## 1. Decisions on PRD Open Questions

The PRD listed five open questions. Resolving them up front so the developer
has an unambiguous target. These are tradeoffs, not verdicts — call out any
you disagree with before implementation starts.

1. **Rounding policy → half-up via `decimal.Decimal`** (PRD OQ-1).
   The codebase already uses integer-cents math; the only fractional moment is
   the percentage multiply. Banker's rounding (Python's `round`) surprises
   readers expecting retail half-up, and is a real footgun for finance review
   later. Cost is one stdlib import. Use:
   `int((Decimal(subtotal_cents) * Decimal(100 - percent) / Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))`.
   No third-party dependency — `decimal` is stdlib, which satisfies `CLAUDE.md`.

2. **Empty-string handling → invalid, returns 400** (PRD OQ-2).
   Treating `""` as "no code" silently swallows a typo where the client meant
   to send a real code and forgot to populate it. Strict rejection is the
   defensive default. Pydantic field validator on the request model handles
   this cleanly.

3. **Code strings → `SAVE5`, `SAVE10`, `SAVE20`** (PRD OQ-3).
   Use the PRD placeholders as the literal strings. If marketing needs
   different strings later, it is a one-line change to the constant. Codes
   live in a module-level dict keyed by canonical (upper-case) form.

4. **Schema shape → two columns on `orders`, no separate table** (PRD OQ-4).
   The PRD's non-goals rule out usage limits, expiry, and stacking. Per the
   project's "no abstractions for a single call site" rule (`CLAUDE.md`),
   adding `Order.discount_code` and `Order.discount_percent` is the right
   shape today. If v2 introduces per-user limits or stacking, that is the
   Rule-of-Three moment to extract a `discounts` table — not now.

5. **Persist `discount_cents` for audit → yes** (PRD OQ-5).
   The cost is one integer column; the benefit is that historical orders
   keep their truth even if we change rounding policy or the percentage
   mapping later. Concretely the column lets `total + discount_cents =
   subtotal_cents` hold as an invariant on every row, which is a much
   cleaner audit story than "recompute from `discount_percent` and hope the
   helper hasn't drifted." This is a write-once value — no extra logic in
   the read path beyond surfacing it.

## 2. File-Level Change List

| File                                  | Change            | Why                                                                 |
| ------------------------------------- | ----------------- | ------------------------------------------------------------------- |
| `src/api/models.py`                   | Modify            | Add three nullable columns to `Order`.                              |
| `src/api/routes/orders.py`            | Modify            | Accept code on create; apply discount; surface on read; reject bad. |
| `src/api/discounts.py`                | **New**           | Constant map + `apply_discount` helper. One file, ~30 lines.        |
| `tests/test_discounts.py`             | **New**           | All PRD acceptance criteria. Uses existing `client` fixture.        |
| `tests/test_orders.py`                | No change         | AC-1 requires existing tests pass unmodified.                       |
| `src/api/deps.py`, `main.py`, etc.    | No change         | No new dependencies, routers, middleware, or auth changes.          |
| `pyproject.toml`                      | No change         | Stdlib `decimal` only.                                              |

That is the entire surface area. Five files touched, two new.

## 3. Module Design

### 3.1 `src/api/discounts.py` (new)

A small module that owns *all* discount logic. The route module imports from
here; nothing else does. This keeps the route handler readable and gives the
test suite something focused to target.

```python
from decimal import Decimal, ROUND_HALF_UP

# Canonical-cased codes. Mapping is the single source of truth.
DISCOUNT_CODES: dict[str, int] = {
    "SAVE5": 5,
    "SAVE10": 10,
    "SAVE20": 20,
}


class InvalidDiscountCode(ValueError):
    """Raised when a non-null code does not match a known entry."""


def normalize_code(raw: str) -> str:
    """Trim + upper-case. Empty (after trim) raises InvalidDiscountCode."""
    code = raw.strip().upper()
    if not code:
        raise InvalidDiscountCode("empty discount code")
    return code


def resolve_percent(raw: str) -> tuple[str, int]:
    """Return (canonical_code, percent). Raises InvalidDiscountCode."""
    code = normalize_code(raw)
    if code not in DISCOUNT_CODES:
        raise InvalidDiscountCode(f"unknown code: {code}")
    return code, DISCOUNT_CODES[code]


def apply_discount(subtotal_cents: int, percent: int) -> tuple[int, int]:
    """Return (discounted_total_cents, discount_cents). Half-up rounding."""
    discount = (
        Decimal(subtotal_cents) * Decimal(percent) / Decimal(100)
    ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    discount_cents = int(discount)
    return subtotal_cents - discount_cents, discount_cents
```

Design notes:
- `tuple[str, int]` return on `resolve_percent` so the route can store the
  canonical (upper-case, trimmed) form regardless of what the client sent.
- `InvalidDiscountCode` is a small sentinel exception. The route catches it
  and re-raises as `HTTPException(400)`. Keeping HTTP concerns out of
  `discounts.py` keeps the helper unit-testable without spinning up
  FastAPI.
- No global state, no I/O, no DB. Pure function module.

### 3.2 `src/api/models.py` (modify)

Add three columns to `Order`. All nullable so existing orders (and orders
created without a code) work without backfill — which matters because the
project drops and recreates the DB between runs but does not migrate.

```python
class Order(Base):
    __tablename__ = "orders"
    # ... existing columns ...
    discount_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    discount_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

Three columns, all nullable, default `None`. No relationship changes, no
new tables.

### 3.3 `src/api/routes/orders.py` (modify)

Three touch points: request model, response model, handler body.

```python
from api.discounts import InvalidDiscountCode, apply_discount, resolve_percent

class OrderCreate(BaseModel):
    items: list[OrderItemIn]
    discount_code: str | None = None  # NEW

class OrderOut(BaseModel):
    id: int
    user_id: int
    total: int
    discount_code: str | None        # NEW
    discount_percent: int | None     # NEW
    discount_cents: int | None       # NEW
    created_at: str
    items: list[OrderItemOut]
```

Handler change (sketch — keep style identical to existing code):

```python
@router.post("", response_model=OrderOut, status_code=201)
def create_order(payload, db, user):
    if not payload.items:
        raise HTTPException(400, "order must have at least one item")

    # Resolve discount BEFORE writing anything, so an invalid code
    # leaves zero rows behind (AC-5).
    discount_code: str | None = None
    discount_percent: int | None = None
    if payload.discount_code is not None:
        try:
            discount_code, discount_percent = resolve_percent(payload.discount_code)
        except InvalidDiscountCode:
            raise HTTPException(400, "invalid discount code")

    order = Order(user_id=user.id, total=0)
    db.add(order)
    db.flush()

    subtotal = 0
    for item in payload.items:
        unit_price_cents = _to_cents(item.unit_price)
        db.add(OrderItem(order_id=order.id, sku=item.sku,
                         quantity=item.quantity, unit_price=unit_price_cents))
        subtotal += unit_price_cents * item.quantity

    if discount_percent is not None:
        total, discount_cents = apply_discount(subtotal, discount_percent)
    else:
        total, discount_cents = subtotal, None

    order.total = total
    order.discount_code = discount_code
    order.discount_percent = discount_percent
    order.discount_cents = discount_cents

    db.commit()
    db.refresh(order)
    return _serialize(order)  # OrderOut with new fields included
```

Key correctness points:
- Validation **before** any `db.flush`-bearing work so AC-5 ("no order
  written") holds. The existing empty-items check already follows this
  pattern, so the new check sits next to it.
- `_to_cents` and the per-item loop stay byte-identical so existing tests
  pass unchanged (AC-1).
- `_serialize` / `OrderOut` construction is centralized to avoid the
  current duplication between `create_order` and `get_order`. *This is a
  small in-place tidy, not a refactor — both functions are already
  building the same shape, and we'd otherwise be duplicating the three
  new fields in two places. Acceptable per Rule of Three (the new fields
  push us to three call sites that need them — POST response, GET
  response, and the implicit "they have to match" constraint).* If you
  prefer to keep both inline (and copy-paste the three new fields), say
  so before implementation.

### 3.4 `tests/test_discounts.py` (new)

One test per PRD acceptance criterion. Uses the existing `client` fixture
from `tests/conftest.py` (in-memory SQLite per test). Suggested test
names — fill in bodies during implementation:

- `test_no_code_unchanged_behaviour` — AC-1
- `test_save5_applied` / `test_save10_applied` / `test_save20_applied` — AC-2
- `test_rounding_half_up_on_fractional_cent` — AC-3 (subtotal `999` +
  `SAVE10` → `total == 899`, `discount_cents == 100`; half-up gives `100`
  not `99`)
- `test_code_is_case_insensitive` — AC-4 (`save10`, `Save10`)
- `test_invalid_code_returns_400_and_writes_nothing` — AC-5 (assert
  `db.query(Order).count() == 0` after the failing POST; needs a small
  db-session fixture or use a follow-up `GET` round-trip)
- `test_get_order_returns_discount_fields` — AC-6
- `test_missing_x_user_id_still_401` — AC-7 (regression guard)
- `test_total_is_non_negative_integer` — AC-8 (covered implicitly by
  other tests but worth a dedicated assertion)

AC-9 ("pytest is green") is the gate, not a test. The full suite must
pass.

## 4. Behavior Notes for the Implementer

- **Read existing patterns first.** `routes/orders.py` is small; mimic
  its style (Pydantic models at top, handler below, helpers underneath).
  No new logging, middleware, or metrics — `CLAUDE.md` rules them out.
- **Don't touch unrelated code.** The `_format_created_at` /
  `add_item_inline` / `adjust_total` helpers at the bottom of
  `orders.py` are unused by the spec; leave them. The `created_at`
  format string in the existing code (`"%Y-%d-%m"`, which is wrong) is
  also out of scope — flagged for separate work.
- **No `X-Discount-Code` header.** The PRD specifies a body field; do
  not invent an alternative transport.
- **Empty string / whitespace.** `OrderCreate.discount_code` is typed
  `str | None = None`. `normalize_code` raises on empty-after-trim, so
  `""` and `"   "` both produce 400, matching FR-4.

## 5. What This Design Does *Not* Do

Explicit so nobody adds them in passing:

- No new tables, no new endpoints, no admin UI.
- No `/discounts` listing route.
- No discount on order *update* (there is no update endpoint).
- No discount on refund (no refund endpoint).
- No event emission, audit log row, or external notification.
- No caching of `DISCOUNT_CODES` — it's a dict literal, already fast.
- No idempotency keys, no rate limiting on the new field.
- No change to auth (still `X-User-Id`).

## 6. Risks and Trade-offs

- **Rounding choice (half-up) ≠ Python default.** Anyone reading
  `apply_discount` for the first time may expect banker's rounding from
  `round()`. The use of `Decimal.quantize(ROUND_HALF_UP)` is explicit
  enough to defuse this, but a one-line comment naming the policy is
  worth it. (This is the one exception to "no comments" — it documents
  a money invariant, which is the WHY case `CLAUDE.md` allows.)
- **Three nullable columns vs. one nullable FK to a `discounts` table.**
  Two-column shape is right for v1 (Rule of Three) but accumulates a
  small migration cost if v2 ships stacking or usage limits. Accepted —
  the alternative is a four-row table and a join from day one for no
  current benefit.
- **`discount_cents` is a write-once denormalization.** If
  `DISCOUNT_CODES` ever changes a percentage value, historical orders
  preserve their original applied amount. That's the intended behaviour
  (audit), but it does mean `discount_percent` and `DISCOUNT_CODES[code]`
  may disagree for old rows. Acceptable; flagging so it doesn't surprise
  during review.
- **No DB constraint enforcing `total + discount_cents == subtotal`.**
  We don't store subtotal, so we can't. Invariant lives in code only.

---

ready for next handoff
