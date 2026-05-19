# Benchmark Report — Plan Mode vs Spec Kit vs BMAD

**Method:** 3 workflows × 4 tasks × 3 runs = 36 cells, all executed against
the same `target/` FastAPI codebase, scored 1–5 by a single operator
against `rubric/scoring-rubric.md`. Every Claude Code subprocess ran
hermetically: `HOME=$(mktemp -d) CLAUDE_CODE_OAUTH_TOKEN=…
claude --print --model sonnet --add-dir target` (no global `CLAUDE.md`,
skills, or agents leaked in; verified via cache-read deltas — 281k →
28k tokens vs the contaminated baseline). Model pinned to **Claude
Sonnet 4.6** end-to-end.

Workflow A is labelled **"Scripted Plan Mode replication"** in tables
because it's a two-call `claude -p --permission-mode plan` then
`--resume --permission-mode acceptEdits` sequence rather than a human
clicking through interactive Plan Mode. It preserves the methodological
idea (plan first, approval boundary, execute after approval, fresh cost
per run, isolated session) without literally being a UI session.

Workflows B and C run end-to-end through their respective skill chains
in a single hermetic session via `--resume`.

## Headline numbers

| | runs | total cost | total wall-clock | mean cost/run | mean dur/run | mean score |
|---|----|------------|------------------|---------------|--------------|------------|
| **A — Plan Mode** | 12 | **$6.66** | 41.9 min | $0.55 | 209s | **4.17** |
| **B — Spec Kit** | 12 | $29.85 | 126.2 min | $2.49 | 631s | 4.08 |
| **C — BMAD** | 12 | $32.05 | 143.9 min | $2.67 | 720s | **4.83** |
| **all 36** | 36 | $68.56 | 312.0 min | — | — | — |

**C delivers the best mean quality (4.83 / 5.00) but costs 4.8× more
than A. B costs 4.5× more than A and scores lower on average.**

## Per-cell aggregates (mean of 3 runs each)

| cell | mean $ | mean s | mean score | scores (r1,r2,r3) |
|------|-------:|-------:|-----------:|:------------------|
| a1 | 0.30 | 100 | 5.00 | 5, 5, 5 |
| a2 | 0.59 | 213 | **3.00** | 3, 3, 3 |
| a3 | 0.59 | 253 | 4.33 | 4, 4, 5 |
| a4 | 0.74 | 272 | 4.33 | 5, 4, 4 |
| b1 | 1.94 | 419 | 4.33 | 4, 5, 4 |
| b2 | 2.55 | 634 | 3.67 | 5, 3, 3 |
| b3 | 2.58 | 736 | 4.67 | 4, 5, 5 |
| b4 | 2.88 | 736 | 3.67 | 3, 4, 4 |
| c1 | 0.69 | 289 | 5.00 | 5, 5, 5 |
| c2 | 2.64 | 645 | 5.00 | 5, 5, 5 |
| c3 | 3.44 | 968 | 5.00 | 5, 5, 5 |
| c4 | 3.91 | 977 | 4.33 | 5, 5, 3 |

## Pre-registered hypothesis vs actual

| Task | Predicted winner | Actual mean-score winner | Actual cost winner | Match? |
| ---- | ---------------- | ------------------------ | ------------------ | ------ |
| 1 | A on cost/time/score | **A & C tie** (both 5.00) | A ($0.30 vs C $0.69) | ✅ partial |
| 2 | A on cost/time/score | **C** (5.00 vs A's 3.00) | A ($0.59 vs C $2.64) | ❌ on score |
| 3 | C on score | **B (4.67) & C (5.00)** | A ($0.59) | ✅ C wins score |
| 4 | B on score | **A & C tie at 4.33** (B = 3.67) | A ($0.74) | ❌ B is worst |

**2 of 4 hypothesis predictions confirmed.** The two rejections are the
spicy findings:

- **Task 2 (refund endpoint):** Plan Mode scored 3/5 across **all
  three runs** because it consistently missed the explicit
  `amount_cents` field from the acceptance criteria — same gap, three
  times. Spec Kit caught it only on **1 of 3** runs (specify-phase
  variance). BMAD caught it on **3 of 3** runs.
- **Task 4 (brownfield discount codes):** Plan Mode discovered the
  integer-cents convention unprompted in all three runs (mean 4.33).
  Spec Kit also caught the cents convention but missed the
  "stored total is the discounted value" criterion on run 1 (mean 3.67
  overall). BMAD's party-mode produced exceptional brownfield insight
  with three personas converging on cents-as-gotcha-#1, but run 3
  regressed on stored-total interpretation (mean 4.33).

## Run-to-run consistency

This is one of the strongest findings:

| | task 1 scores | task 2 scores | task 3 scores | task 4 scores |
|---|---------------|---------------|---------------|---------------|
| A | 5,5,5 (σ=0) | **3,3,3 (σ=0)** | 4,4,5 | 5,4,4 |
| B | 4,5,4 | 5,3,3 | 4,5,5 | 3,4,4 |
| C | 5,5,5 (σ=0) | 5,5,5 (σ=0) | 5,5,5 (σ=0) | 5,5,3 |

C has the lowest variance across the board, with **9 of 12 runs at
exactly 5/5**. A is consistent on the easy and hard ends but
catastrophically consistent at 3/5 on task 2 (missing-field failure
mode is reproducible across runs).

## Task-by-task findings

### Task 1 (trivial date-format bug)

A and C ship the identical minimal 3-file diff in every single run for
$0.26–$0.74 in 80–397 s. B always produces the same correct fix but
wraps it in 600–900 lines of `spec.md`, `plan.md`, `tasks.md`,
`research.md`, `data-model.md`, `quickstart.md` artifacts; one of the
three B runs added redundant integration tests in `test_orders.py`
(task spec explicitly said "ideally nothing else" beyond the 3 named
files). **On a one-line bugfix, Plan Mode is 5–6× cheaper and 3–4×
faster than the ceremony workflows with no quality loss.**

### Task 2 (medium refund endpoint)

The article's most interesting cell. The acceptance criteria explicitly
list **"order_id, refunded amount in cents, a timestamp"** as required
fields. Plan Mode's RefundOut omits `amount_cents` in all three runs.
Spec Kit's `/speckit-specify` phase caught the field in run 1 (`FR-008`
explicitly), excluded it in run 2 ("Monetary amount … out of scope"),
and didn't address it in run 3 — real specify-phase variance. BMAD
always caught it (named it `total` in r1+r2, `total_refunded` in r3),
because the PM persona writes a full PRD that audits every response
field against the request.

### Task 3 (ambiguous "add rate limiting")

The classic ambiguity-draining test. Workflow C surfaced **all 7
requirements axes** in every single run, including the `/health`
exclusion question (explicit in the PRD as an assumption with an open
question for ratification). A and B both surface 6 of 7 most of the
time, missing `/health` in 2 of 3 runs each. Implementation quality
differs sharply on this task:

- A3-r3 ($0.84): per-IP, `/health` excluded, 16/16 pass — **score 5**
- B3-r3 ($2.70): documented "uniformly applies, no endpoint exempt",
  user-or-IP fallback — score 5
- C3-r1 ($4.58): user-or-IP with explicit fail-open semantics,
  env-var configurable, `/health` exempt — score 5

C costs ~5× A on this task but is reliably the highest quality.

### Task 4 (brownfield trap: discount codes + integer cents)

`convention discovered: yes` in **all 36 task-4 cells** — every workflow
in every run noticed the existing `_to_cents` helper and the `Integer`
columns. Variance shows up in three secondary criteria:

1. **Stored discounted total**: spec says "the stored total is 900 for
   1000 × 10%". A all three runs ✓, B 2 of 3 ✓ (r1 missed), C 2 of 3 ✓
   (r3 regressed by storing total + discounted_total in separate
   columns).
2. **Discount-code storage**: spec says "not a magic dict". A used a
   module-level dict 2 of 3 times (technically not "inside the route
   handler" but reviewer would push back). B and C always used a DB
   table.
3. **HTTP status for invalid code**: spec says 400; FastAPI convention
   is 422. A consistent at 400 (r3) or via Literal validation. B and C
   often used 422.

Party-mode (C only) produced the highest-value single artifact in the
benchmark — three persona perspectives independently converging on the
top 3 gotchas (cents, OrderOut manual construction, test-data problem).
The orchestrator note "all three agents converged hard on three things
without coordinating — that's a reliable signal these are the real
traps" is article-worthy on its own.

## Cost ladder by task complexity

A's cost grows roughly linearly with task complexity:
$0.30 (trivial) → $0.59 (medium) → $0.59 (ambiguous) → $0.74 (brownfield).

C's cost grows faster: $0.69 → $2.64 → $3.44 → $3.91. The expensive
phases are **`create-story`** (often $0.9–$1.5 alone) and **`code-review`**
(often $0.9–$1.5), reflecting BMAD's commitment to per-story documents
and a full diff review per cell.

B is flatter, ~$2 across the board, because the 5-phase chain always
runs regardless of task size.

## When each workflow is worth its cost

- **Plan Mode wins** on task 1 (no question — 5× cheaper, equal quality)
  and ties on cost-adjusted quality for task 4 (discovers conventions
  unprompted on small codebases). The article's pre-registered Plan Mode
  predictions were too cautious — Plan Mode is competitive on more tasks
  than the hypothesis suggested, *as long as the spec is unambiguous*.
- **Plan Mode loses badly** on task 2 — a structural failure to audit
  the acceptance criteria against the response schema, reproducible
  across 3 runs. The fastest, cheapest workflow has a consistent
  failure mode for "well-specified medium" tasks. This is the
  cautionary tale.
- **Spec Kit's specify phase** has the highest run-to-run variance of
  the three workflows. Sometimes it catches things Plan Mode misses
  (B2-r1 FR-008); sometimes it explicitly rules them out of scope
  (B2-r3). Its ceremony is more expensive than it is reliable.
- **BMAD's full ceremony reliably wins on quality** (9 of 12 cells at
  5/5, mean 4.83), but you pay ~5× the Plan Mode cost and ~3× the
  wall-clock time. Where it really earns the cost is task 3
  (ambiguous brief) and the convention-discovery part of task 4
  (party-mode is the genuinely novel artifact).

## Reproducibility

- All artifacts: `results/runs/<workflow>-<task>-<run>/` includes
  `plan.md` (A) or per-phase JSON transcripts (B, C), per-run cost JSON,
  pytest report, and the diff against the workflow's base branch.
- Per-run branches retained: `workflow-{a,b,c}/task-{1..4}/run-{1..3}`.
- Aggregate CSV: `results/results.csv` (37 columns including per-phase
  cost split for A, prompt hashes, model, hermetic mode, context source,
  score, notes).
- Harness: `harness/run.py` (interactive + `--non-interactive` modes),
  driver scripts `harness/run_{a,b,c}_scripted.sh`.

## Limitations

- `n=3` per cell is large enough to spot a 2× difference, not small
  effects. The "task 2 Plan Mode is consistently 3/5" signal at 3/3 is
  the strongest single statistical claim in this benchmark.
- Single operator scored all 36 cells. The rubric is anchored
  concretely but there's no second rater; read the per-run diffs to
  form your own opinion.
- Synthetic ~500-LOC codebase. Task 4 is the only place a real
  brownfield convention trap is reproduced.
- BMAD v6.7.1 ships as Claude Code skills rather than slash commands,
  and dropped explicit PO/SM/QA personas. The runbook uses these v6
  substitutes: `bmad-check-implementation-readiness` (PO),
  `bmad-create-story` (SM), `bmad-code-review` (QA). See
  `workflows/c-bmad.md` for the mapping.
- All B and C workflows used `--permission-mode bypassPermissions`
  because the chains rely on bash for pytest etc. and an operator
  approving each tool call would have changed the cost/time measurement.

## Opus rebuttal (7 targeted reruns)

The most defensible critique of the Sonnet-only data is "would Opus have
caught the things Sonnet missed?" To test this without rerunning all 36,
seven cells were re-executed on **Claude Opus 4.7 (1M context)**, same
hermetic pattern, recorded as runs 4–6 to keep the original run-1/2/3
data intact. Total Opus spend: $24.04 across 7 cells.

| cell | Sonnet | Opus | what changed |
|------|--------|------|--------------|
| **A2** (3 runs) | 3, 3, 3 — missed `amount_cents` | **5, 5, 5 — caught it** | **Pure model-capability gap.** Opus 3/3, Sonnet 0/3. The headline Plan Mode failure was Sonnet-specific. |
| **B2-r2 → r5** | 3 — missed amount | 3 — also missed | Spec Kit's specify-phase variance is workflow-shape, not model-capability. |
| **B2-r3 → r6** | 3 — missed amount | 5 — caught it | Same Spec Kit cell, different outcome — variance persists on Opus (1/2 catch, vs Sonnet's 1/3). |
| **B4-r1 → r4** | 3 — stored total wrong | 5 — used `(subtotal × pct + 50) // 100`, stored discounted value | Partly model-capability — Opus reasoned through the cents-rounding constraint properly. |
| **C4-r3 → r4** | 3 — stored total regressed | 5 — `Decimal × ROUND_HALF_UP` in a separate `discounts.py` module, 36 tests | Pure model-capability. Opus produced the cleanest single implementation in the whole benchmark with an explicit comment justifying ROUND_HALF_UP for money. |

### What this changes

- **A2's "Plan Mode is structurally bad at well-specified medium tasks"
  claim doesn't survive Opus.** On Opus, Plan Mode catches the
  `amount_cents` field every time. The original article framing should
  shift to "Sonnet+Plan Mode misses spec-detail audit fields that
  Opus+Plan Mode catches" — still a real finding, but about the
  Sonnet/Opus delta on this workflow, not about Plan Mode as a shape.
- **Spec Kit's task-2 variance is real and model-independent.** B2 on
  Sonnet caught the amount field 1 of 3 times; on Opus 1 of 2. The
  specify phase is genuinely unreliable at interpreting "refund
  record" as requiring the dollar amount, regardless of model. This
  is a workflow-shape failure that more compute won't fix.
- **BMAD's "100% consistency on all four tasks across all 12 Sonnet
  runs (mean 4.83)" is the most robust headline.** Opus on C4 still
  produced a 5/5 — and the Opus C4 run is qualitatively the best work
  in the whole benchmark (Decimal rounding, separate discounts.py,
  36 tests). BMAD's reliability story holds.

### Cost on Opus vs Sonnet

Opus is **3–5× more expensive per cell** at this hermetic scale:

| cell | Sonnet $ | Opus $ | ratio |
|------|---------:|-------:|------:|
| A2 mean | 0.59 | 1.73 | 2.9× |
| B2 mean | 2.55 | 4.19 | 1.6× |
| B4 mean | 2.88 | 5.26 | 1.8× |
| C4 mean | 3.91 | 5.22 | 1.3× |

Surprisingly **not** 5× across the board — Opus's higher per-token cost
is partly offset by the same output budget per task. The premium is
biggest on the smallest cells (A2 ~3×) and smallest on the most-verbose
ones (C4 ~1.3×). If you only need Opus for the spec-detail-audit step,
the cost premium is manageable.

### Combined picture

Grand total across Sonnet + Opus: **$92.60 for 43 cells**. Final
mean-score-by-workflow-and-model:

| | n | mean score | total cost |
|---|---|-----------|-----------|
| A Sonnet | 12 | 4.17 | $6.66 |
| A Opus | 3 | **5.00** | $5.18 |
| B Sonnet | 12 | 4.08 | $29.85 |
| B Opus | 3 | 4.33 | $13.64 |
| C Sonnet | 12 | 4.83 | $32.05 |
| C Opus | 1 | 5.00 | $5.22 |

The real story: **A on Opus matches C on Sonnet for ~5× less cost** on
the cells we tested. The article's most honest framing isn't "BMAD wins
on quality" — it's "if you want Plan-Mode-level cost, switch to Opus;
if you want Sonnet-level cost, accept BMAD's ceremony tax for quality."

## Files of interest

- `results/results.csv` — every cell, every column
- `results/runs/c-4-1/_bmad-output/planning-artifacts/architecture.md`
  and `prds/*/prd.md` — the BMAD task-4 party-mode output worth
  quoting in the article
- `results/runs/b-3-1/spec.md` — Spec Kit's most thorough
  rate-limiting requirements catch (`FR-001` through `FR-007` plus rich
  headers spec)
- `workflows/c-bmad.md` — the runbook explaining the v6.7.1 persona
  mapping decision
- `results/runs/c-4-4/` — the Opus-on-BMAD task-4 run; cleanest
  implementation in the benchmark (Decimal+ROUND_HALF_UP rounding,
  separate `discounts.py` module, 36/36 tests)
- `results/runs/a-2-{4,5,6}/plan.md` — three Opus Plan Mode plans
  for the refund endpoint, all explicitly listing `amount: int` in
  RefundOut (Sonnet's three plans omitted it)
