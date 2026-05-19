# Task 4 — Brownfield

## Prompt (paste verbatim to the agent)

Add a feature where users can apply a percentage discount code at checkout. Discounts can be 5%, 10%, or 20%. Include tests.

## Acceptance criteria

- A discount code can be applied either as part of the order-creation request or via a separate endpoint (workflow's choice).
- Only the three percentages above are accepted; anything else returns a `400`.
- Discount codes are stored somewhere durable (table, enum, or seed data) — not hardcoded inside the route handler as a magic dict.
- **All monetary values remain integer cents end-to-end.** The discount must not introduce floats into stored money. Concretely:
  - The discounted order `total` in the database is an integer.
  - For an order whose pre-discount total is `1000` cents (`$10.00`) and a 10% discount, the stored total is **`900`** (not `900.0`, not `899`, not `901`).
  - For a pre-discount total of `1999` cents and a 5% discount, the stored total is whatever the agent's stated rounding rule produces — but it must be an integer, and the rounding rule must be either obvious from the code or explicitly documented in the diff.
  - No `Float` SQLAlchemy column is added for money.
- The API response surface stays consistent with the existing code: monetary fields in responses continue to be integers (cents), not dollars-as-floats.
- `pytest` passes, including new tests covering: each of the three valid percentages, an invalid percentage, the order total being correctly recomputed.

## What this probes

Whether the workflow's discovery phase actually reads the existing code
deeply enough to notice the integer-cents convention before generating
implementation code. There is **no hint** about this convention in any
shared `CLAUDE.md`, runbook, or prompt — it has to be discovered the way
a new engineer would discover it: by reading `models.py`, `routes/orders.py`,
and the existing tests.

When scoring this task, the operator should explicitly note in `notes`:
"convention discovered: yes / no — evidence: ___". That single observation
is likely the most quotable data point in the whole benchmark.
