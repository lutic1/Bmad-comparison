# sdd-framework-benchmark

A small, transparent benchmark comparing three AI coding workflows on a fixed
set of tasks against the same synthetic codebase. Companion repository to a
Medium article testing whether external Spec-Driven Development frameworks
measurably improve outcomes over Claude Code's native Plan Mode.

> **Article:** _(link TBD — placeholder until published)_

## What's being compared

| ID | Workflow | Description |
| -- | -------- | ----------- |
| A  | **Plan Mode** | Claude Code with a project `CLAUDE.md` and built-in Plan Mode. No external framework. |
| B  | **Spec Kit** | GitHub's Spec Kit toolkit: `constitution → specify → plan → tasks → implement`. |
| C  | **BMAD** | BMAD method: Analyst → PM → Architect → PO → SM → Dev → QA personas with handoffs. |

Each workflow is run against four tasks of escalating complexity, three times
each, for a total of **3 workflows × 4 tasks × 3 runs = 36 runs**.

## The tasks

| # | Task | What it probes |
| - | ---- | -------------- |
| 1 | Fix a subtle date-format bug | Trivial localised work — does ceremony help or just add cost? |
| 2 | Add a `POST /orders/{id}/refund` endpoint | Medium, well-specified — typical greenfield slice. |
| 3 | "Add rate limiting to the API." | Ambiguous one-liner — which workflow surfaces the missing requirements? |
| 4 | Add percentage discount codes at checkout | Brownfield trap — the codebase stores money as integer cents, undocumented. |

## Pre-registered hypothesis

Stated **before** any run is executed, so it can be checked against the
results regardless of how they land:

- **Plan Mode wins tasks 1 and 2** on cost, time, and subjective score.
  Lightweight ceremony beats heavy ceremony when the spec is already clear.
- **Spec Kit wins task 4** on subjective score. Its explicit specify/plan
  separation creates a slot where the agent is forced to read the codebase
  and write down constraints before coding — exactly the moment the cents
  convention should be discovered.
- **BMAD wins task 3** on subjective score but loses badly on cost and time.
  The Analyst → PM handoff is well-suited to draining ambiguity out of a
  one-sentence brief; the price is many more turns and tokens.

If the results contradict any of these predictions, that's a more
interesting finding, not a less interesting one.

## Hypothesis status

| Task | Predicted winner (score) | Actual winner (score) | Match? |
| ---- | ------------------------ | --------------------- | ------ |
| 1    | A — Plan Mode            | _TBD_                 | _TBD_  |
| 2    | A — Plan Mode            | _TBD_                 | _TBD_  |
| 3    | C — BMAD                 | _TBD_                 | _TBD_  |
| 4    | B — Spec Kit             | _TBD_                 | _TBD_  |

## Methodology

1. The `target/` directory contains a small FastAPI service (~500 LOC,
   users + orders, SQLAlchemy + SQLite, pytest). It is the codebase under
   test for every run.
2. All three workflows are given the **same** `CLAUDE.md`. None of the
   workflow-specific docs tip the agent off about the integer-cents
   convention; that has to be discovered.
3. Each run happens on a fresh branch off `main`:
   `workflow-{a,b,c}/task-{1..4}/run-{1..3}`.
4. The harness (`harness/run.py`) wraps each run, captures git diff stats,
   pytest results, wall-clock duration, token / cost figures (entered
   manually — see _Limitations_), and a 1–5 subjective score using the
   rubric in `rubric/scoring-rubric.md`.
5. Per-run artifacts (diffs, transcripts) land in `results/runs/`.
   Aggregate metrics append to `results/results.csv`.
6. `harness/analyze.ipynb` reads the CSV and produces the charts that
   ship with the article.

## How to reproduce

```bash
git clone <this repo>
cd sdd-framework-benchmark

# Install the target codebase and verify tests pass before you start
cd target
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
cd ..

# Run a single cell — example: workflow A, task 1, run 1
python harness/run.py --workflow a --task 1 --run 1
```

You'll need to install each workflow's tooling separately — see
`workflows/{a,b,c}-*.md` for the exact commands and the prerequisites
checklist in the final section of this README.

## Limitations / caveats

- **n=3 per cell is exploratory, not publication-grade.** The numbers are
  large enough to spot a 2× difference but not small effects.
- **Single operator → scoring bias is possible.** The 1–5 rubric is
  anchored concretely (see `rubric/scoring-rubric.md`) but there is no
  second rater. Read the per-run diffs in `results/runs/` and form your
  own opinion.
- **The harness is human-in-the-loop.** It can't drive Claude Code,
  Spec Kit, or BMAD interactively, so the operator runs the workflow and
  pastes token / cost numbers back. This is a deliberate trade — fully
  automating three different agent frameworks would have taken longer
  than running the benchmark.
- **Synthetic codebase.** ~500 LOC of FastAPI doesn't reflect every
  brownfield pain (no legacy migrations, no untyped Python 2 corners,
  no decade of dead code). Task 4 is the one place a real-world
  convention trap is reproduced.
- **Token counting is approximate for B and C.** Spec Kit and BMAD run
  through multiple commands / personas; the operator sums per-step
  costs by hand. Plan Mode uses Claude Code's `/cost`.

## Pre-run checklist (operator)

Before the first run:

- [ ] Python 3.11+ available
- [ ] `cd target && pip install -e ".[dev]" && pytest` — all tests pass
- [ ] Claude Code CLI installed and authenticated (`claude --version`)
- [ ] Anthropic API key set (`ANTHROPIC_API_KEY`)
- [ ] Spec Kit installed — see `workflows/b-spec-kit.md`
- [ ] BMAD installed — see `workflows/c-bmad.md`
- [ ] Read `rubric/scoring-rubric.md` and internalise the anchors
- [ ] Decide a run order and stick to it (recommend: A1 B1 C1 A2 B2 C2 …
  to avoid within-workflow learning effects within a task)

## Repository layout

```
sdd-framework-benchmark/
├── target/                      # the synthetic codebase under test
├── tasks/                       # exact prompts pasted into each agent
├── workflows/                   # step-by-step runbooks per workflow
├── harness/                     # run.py, score.py, analyze.ipynb
├── rubric/                      # 1-5 scoring rubric with anchors
├── results/                     # results.csv + per-run artifacts
└── article/charts/              # PNG output destination for the notebook
```
