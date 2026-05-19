# Workflow B — Spec Kit

GitHub's Spec Kit is a slash-command toolkit on top of an agent
(Claude Code, Cursor, etc.). It splits a task into five phases:
`constitution → specify → plan → tasks → implement`.

## One-time setup

```bash
# Install Spec Kit per its docs
# https://github.com/github/spec-kit
# (Typically: install the spec-kit CLI, then initialise inside the project.)

# Verify
speckit --version
```

Spec Kit drops its slash commands into the agent's command directory.
After installing inside the `target/` directory you should see
`/speckit.constitution`, `/speckit.specify`, `/speckit.plan`,
`/speckit.tasks`, `/speckit.implement` available in Claude Code.

## Per-run procedure

```bash
python harness/run.py --workflow b --task <N> --run <M>
```

When the harness pauses, in another shell:

```bash
cp workflows/claude-md-template/CLAUDE.md target/CLAUDE.md
cd target
# initialise spec-kit if it isn't already on this branch
speckit init   # follow the prompts, choose Claude Code as the agent
claude
```

Inside Claude Code, run the five Spec Kit commands in sequence. Use the
same `CLAUDE.md` as workflow A (no extra hints).

### 1. `/speckit.constitution`

Paste the contents of the box below verbatim when prompted for the
constitution content:

```
# Project constitution

- Stack: Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest.
- Idiomatic FastAPI: small route functions, Pydantic models for
  request and response shapes, dependency injection via Depends.
- Tests are non-optional. Minimum 80% line coverage on changed files.
  Every new route ships with happy-path and at least one error-path
  test.
- Conventional commits: feat:, fix:, refactor:, test:, docs:, chore:.
- No new third-party dependencies without a stated justification.
- Type hints on every public function and route handler.
- Don't refactor unrelated code in the same change.
```

### 2. `/speckit.specify`

Paste the **exact** prompt from `tasks/0N-*.md` (only the `## Prompt`
body, not the acceptance criteria).

Let Spec Kit produce a spec. If it asks clarifying questions
(particularly for task 3), answer them honestly — do not pre-feed it
the acceptance criteria. For tasks 1, 2, and 4, answer "use your
best judgement" or the equivalent for any question Spec Kit can
reasonably resolve from the codebase.

### 3. `/speckit.plan`

Accept defaults. Let Spec Kit produce its implementation plan.

### 4. `/speckit.tasks`

Accept defaults. Let Spec Kit decompose into tasks.

### 5. `/speckit.implement`

Let Spec Kit run the implementation tasks end-to-end. Approve tool
calls as they come up; do not steer mid-execution beyond approvals.

When done:

- Run `pytest` to sanity check.
- Use `/cost` after each Spec Kit phase if your agent surfaces it, OR
  `/cost` once at the end if it aggregates. Sum manually if needed.
- Exit Claude Code.

Back in the harness shell:

- Confirm completion (`y`).
- Paste the **summed** token / cost across all five Spec Kit phases.
- Score using the rubric.
- For task 3, note in `notes` how many requirements bullets the spec
  surfaced (counted by reading the generated `spec.md`).
- For task 4, note whether the spec captured the integer-cents
  convention.

## Cleanup between runs

```bash
rm -f target/app.db
# Spec Kit drops files into target/specs/ and target/memory/. The
# harness's branch reset handles those automatically since they're
# part of the diff against main.
```

## Notes on this workflow

- Don't manually edit Spec Kit's generated artifacts to "help" it.
- If `/speckit.implement` errors out partway, let it retry once on its
  own. If it errors a second time, record what happened in `notes`
  and stop the run — that's a real outcome, not a do-over.
