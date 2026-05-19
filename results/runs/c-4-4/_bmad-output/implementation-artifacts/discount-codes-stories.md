---
title: Stories — Percentage Discount Codes at Checkout
status: ready-for-dev
created: 2026-05-19
related_prd: ../planning-artifacts/prds/prd-target-2026-05-19/prd.md
related_design: ../planning-artifacts/architecture/discount-codes-design.md
---

# Stories — Percentage Discount Codes at Checkout

## Sequencing rationale

This feature is small. Honest split is **two stories**:

1. **S1 — Discount helper module (pure).** No DB, no FastAPI. Pure function. Unit-testable in isolation. Fast feedback loop. Safe to merge as standalone "dead code" because nothing else imports it yet.
2. **S2 — Wire discount into order flow.** Adds the columns, updates Pydantic models, updates the POST handler, exposes on GET, ships integration tests covering every PRD acceptance criterion.

A third story (e.g. "expose on GET only") would be artificial — `OrderOut` is shared between POST and GET, so AC-6 has to land in S2 anyway. Two stories is the right floor.

Both stories together satisfy PRD AC-1 through AC-9. S1 alone satisfies none of them (it has no callers); S2 alone is not possible without S1 (the helper doesn't exist). Sequence is strict: S1 → S2.

---

## Story S1 — Discount helper module

**Status:** ready-for-dev
**Estimate:** ~30 minutes of focused work.

**Ready-for-dev brief.**
Create a new module `src/api/discounts.py` containing the canonical-cased
`DISCOUNT_CODES` mapping (`SAVE5` → 5, `SAVE10` → 10, `SAVE20` → 20), a small
`InvalidDiscountCode(ValueError)` sentinel exception, a `normalize_code(raw:
str) -> str` helper that trims and upper-cases input and raises
`InvalidDiscountCode` on empty-after-trim, a `resolve_percent(raw: str) ->
tuple[str, int]` helper that returns the canonical code and percent (raising
`InvalidDiscountCode` for unknown codes), and an `apply_discount(subtotal_cents:
int, percent: int) -> tuple[int, int]` function that returns
`(discounted_total_cents, discount_cents)` using `decimal.Decimal` with
`ROUND_HALF_UP`. The module must be importable as `from api.discounts import
...`, must not import from `api.routes` or `api.deps` (no circular deps),
must use only stdlib (`decimal` is fine; no new dependencies in
`pyproject.toml`), and must freeze `DISCOUNT_CODES` against accidental
mutation (`types.MappingProxyType`). Add a companion test file
`tests/test_discount_helpers.py` that covers the pure-function behaviour:
each tier returns the right percent, lookup is case-insensitive and
whitespace-tolerant, unknown / empty / whitespace-only inputs raise
`InvalidDiscountCode`, and rounding follows half-up at the half-cent boundary
(e.g. `apply_discount(999, 5) == (949, 50)`, `apply_discount(1000, 10) ==
(900, 100)`). Do **not** modify `models.py`, `routes/orders.py`, or any other
file — this story is purely additive. `pytest` must be green at the end.

**Acceptance criteria.**

- **S1-AC-1.** `src/api/discounts.py` exists and exposes `DISCOUNT_CODES`,
  `InvalidDiscountCode`, `normalize_code`, `resolve_percent`, `apply_discount`.
- **S1-AC-2.** `DISCOUNT_CODES` is read-only at runtime (mutating it raises).
- **S1-AC-3.** `normalize_code("  save10  ")` returns `"SAVE10"`.
- **S1-AC-4.** `normalize_code("")` and `normalize_code("   ")` both raise
  `InvalidDiscountCode`.
- **S1-AC-5.** `resolve_percent("Save20")` returns `("SAVE20", 20)`.
- **S1-AC-6.** `resolve_percent("NOPE")` raises `InvalidDiscountCode`.
- **S1-AC-7.** `apply_discount(1000, 10) == (900, 100)` (clean tier math).
- **S1-AC-8.** `apply_discount(999, 5) == (949, 50)` (half-up boundary; the
  `Decimal` calculation `999 * 5 / 100 == 49.95` rounds to `50`, not `49`).
- **S1-AC-9.** `apply_discount` always returns two non-negative integers.
- **S1-AC-10.** No new entries in `pyproject.toml`. Full `pytest` is green.

**Convention gotchas the dev must respect (from the convention sweep):**

- Stdlib only — `Decimal` from `decimal`, `MappingProxyType` from `types`.
- Module must not import from `api.routes` or `api.models` (keeps it pure
  and circular-import-safe).
- No logging, no metrics, no docstrings beyond what already exists in the
  repo. One short comment is acceptable to name the rounding policy
  ("half-up via Decimal.quantize") because it's a money invariant.
- Tests live in `tests/test_discount_helpers.py` (new file). Plain test
  functions, literal data — match the style in `tests/test_dates.py`. Do
  not introduce `pytest.mark.parametrize` as a new convention.

---

## Story S2 — Apply discount on order create and surface on read

**Status:** ready-for-dev (blocked by S1)
**Estimate:** ~60–90 minutes of focused work.

**Ready-for-dev brief.**
With `api.discounts` in place from S1, wire discounts into the order flow.
In `src/api/models.py`, add three nullable columns to `Order` using
SQLAlchemy 2.x `Mapped[Optional[...]]` style: `discount_code:
Mapped[Optional[str]] = mapped_column(String(32), nullable=True,
default=None)`, `discount_percent: Mapped[Optional[int]] =
mapped_column(Integer, nullable=True, default=None)`, and `discount_cents:
Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)`.
In `src/api/routes/orders.py`, add an optional `discount_code: str | None =
None` field to `OrderCreate`; add the three matching nullable fields to
`OrderOut`; in `create_order`, **resolve and validate the code via
`resolve_percent` before `db.add(order)` / `db.flush()`** so an invalid
code returns `HTTPException(400, "invalid discount code")` with zero rows
written; on a valid code, compute the discounted total via `apply_discount`,
store the canonical code / percent / discount_cents on the row, and set
`order.total` to the discounted amount; on a missing code, behaviour is
byte-identical to today. Update `get_order` so its `OrderOut` construction
includes the three new fields (do not extract a `_serialize` helper —
inline duplication is the conventional choice at two call sites; revisit
extraction only if a third site appears). Do **not** modify
`OrderCreate`'s extra-field policy, do **not** touch the `%Y-%d-%m`
date format string, do **not** modify or remove the dead helpers
(`adjust_total`, `add_item_inline`, `_format_created_at`), and do **not**
add logging or middleware. Add a new test file `tests/test_discounts.py`
that uses the existing `client` and `db_engine` fixtures from
`tests/conftest.py` to cover every PRD acceptance criterion AC-1 through
AC-9. The full `pytest` suite must be green at the end — including all
existing tests in `tests/test_orders.py` (AC-1) and `tests/test_dates.py`.

**Acceptance criteria (cited from PRD `prd.md` §5).**

- **S2-AC-1 ⇒ PRD AC-1.** `POST /orders` with no `discount_code` returns the
  same shape and `total` as before. All existing `tests/test_orders.py`
  tests pass unmodified.
- **S2-AC-2 ⇒ PRD AC-2.** One test per tier: `SAVE5`, `SAVE10`, `SAVE20`
  applied to a known subtotal produce the expected discounted integer
  `total` in cents.
- **S2-AC-3 ⇒ PRD AC-3.** Rounding boundary: subtotal `999` cents with
  `SAVE10` yields `total == 899` and `discount_cents == 100` (half-up
  rounding of `99.9 → 100`).
- **S2-AC-4 ⇒ PRD AC-4.** Case-insensitivity: `save10` and `Save10`
  produce the same result as `SAVE10`; stored `discount_code` is
  canonical `"SAVE10"`.
- **S2-AC-5 ⇒ PRD AC-5.** `POST /orders` with `discount_code: "NOPE"`
  returns `400` and detail `"invalid discount code"`; opening a session
  from the `db_engine` fixture shows zero new rows in `orders` and zero
  new rows in `order_items`. Same for `discount_code: ""`.
- **S2-AC-6 ⇒ PRD AC-6.** `GET /orders/{id}` for an order created with
  `SAVE20` returns `discount_code: "SAVE20"`, `discount_percent: 20`,
  `discount_cents: <integer>`; for an order created without a code, all
  three fields are present in the response body and are exactly `None`
  (use `body.get("discount_code") is None`, not `"discount_code" not in
  body`).
- **S2-AC-7 ⇒ PRD AC-7.** A `POST /orders` request without `X-User-Id`
  still returns 401. A request with an unknown user id still returns 401.
- **S2-AC-8 ⇒ PRD AC-8.** Every stored `Order.total` and
  `Order.discount_cents` value in every test is a non-negative integer.
- **S2-AC-9 ⇒ PRD AC-9.** `pytest` runs green end-to-end. Do not commit
  if it isn't.

**Convention gotchas the dev must respect (from the convention sweep):**

- **Validate the code BEFORE `db.add(order)` / `db.flush()`** — mirrors the
  existing empty-items check. This is what makes S2-AC-5 ("no row
  written") true.
- **Catch `InvalidDiscountCode` at the route boundary and raise
  `HTTPException(400, ...)`.** A bare `InvalidDiscountCode` propagates as
  HTTP 500 because FastAPI only auto-catches `HTTPException`. Match the
  existing pattern in `create_order` (it already raises `HTTPException`
  directly for empty items).
- **Use `Mapped[Optional[str]]` / `Mapped[Optional[int]]` declarative
  style.** Raw `Column(...)` is wrong; everything else in `models.py`
  uses `Mapped[...]` + `mapped_column(...)`.
- **`OrderOut` is built twice (POST + GET).** Both sites must include the
  three new fields. Inline duplication is correct here — do not extract
  a `_serialize` helper.
- **Money I/O stays asymmetric.** Discount input is the code string only;
  output exposes `discount_cents` as an integer (no float dollars on
  output). Matches the existing `OrderItemIn.unit_price: float` (in) →
  `OrderItemOut.unit_price: int` (out) shape.
- **`OrderCreate` keeps Pydantic v2 default (extra fields ignored).** Do
  not add `model_config = ConfigDict(extra="forbid")` — that is a
  breaking contract change for existing callers and is out of scope.
- **Do not touch `_to_cents` or `add_item_inline`** — three rounding
  policies coexist by design. The new policy (half-up) lives only in
  `apply_discount`.
- **Do not touch the `%Y-%d-%m` date format string** anywhere — bug is
  pinned by `tests/test_dates.py`. New `OrderOut` construction must pass
  `created_at` through the same buggy path unchanged.
- **No new fixtures in `conftest.py`.** Build a session inline from
  `db_engine` when you need to assert "no row written".
- **Keep the route fully synchronous.** No `asyncio.create_task`;
  `StaticPool` in-memory SQLite does not survive thread boundaries in
  tests.
- **Operator note in the PR description:** `app.db` must be deleted before
  restart so the new columns materialize via `Base.metadata.create_all`
  (no migrations, per `CLAUDE.md`).

---

## What this stories file does not cover

- No admin endpoint, no expiry, no usage limits, no stacking, no caps
  (PRD non-goals §3). Do not infer these from "while you're here".
- No fix for the `%Y-%d-%m` date bug. Separate work.
- No consolidation of the three cents-conversion helpers. Separate work.
- No removal of the dead helpers in `routes/orders.py`. Separate work.

---

## Handoff

S1 and S2 are both `ready-for-dev`. Execute in order: S1 first (it is
self-contained and unblocks S2), then S2 (which has every PRD acceptance
criterion mapped). Dev agent (`bmad-agent-dev` / Amelia) should pick up S1
now.
