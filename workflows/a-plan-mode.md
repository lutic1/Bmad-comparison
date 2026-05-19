# Workflow A — Claude Code Plan Mode

The control arm. No external framework — just Claude Code with a project
`CLAUDE.md` and built-in Plan Mode.

## One-time setup

```bash
# Install Claude Code if you haven't
# https://docs.claude.com/en/docs/claude-code
claude --version

# Authenticate
claude login
```

## Per-run procedure

Run from the repo root.

```bash
# 1. Start the harness — it will checkout a fresh branch and prompt you
python harness/run.py --workflow a --task <N> --run <M>
```

When the harness pauses for the operator step, do this:

```bash
# 2. In another shell, copy the CLAUDE.md template into the target
cp workflows/claude-md-template/CLAUDE.md target/CLAUDE.md

# 3. Start Claude Code inside the target directory
cd target
claude
```

Inside the Claude Code session:

1. Toggle Plan Mode (`Shift+Tab` until the status line shows "plan mode").
2. Paste the **exact** prompt from `tasks/0N-*.md` (only the body of the
   `## Prompt` section, not the acceptance criteria).
3. Let Claude produce a plan.
4. Accept the plan (Plan Mode will prompt you).
5. Let it execute. Do not steer mid-execution beyond approving tool
   calls.
6. When Claude says it's done, run `pytest` to sanity check.
7. Type `/cost` and copy the token and dollar numbers.
8. Exit Claude Code (`/exit`).

Back in the harness shell:

- Confirm completion (`y`).
- Paste the token counts and cost when prompted.
- Score the run using `rubric/scoring-rubric.md`.
- Add free-form notes — at minimum:
  - For task 3: how many of the seven requirements bullets did Plan Mode
    surface vs assume?
  - For task 4: convention discovered: yes / no, with evidence.

## Cleanup between runs

The harness handles branch creation. You should:

```bash
# From the repo root
rm -f target/app.db          # reset the sqlite store
# Stay on the run branch — the harness will switch back to main for
# the next run.
```

## Notes on this workflow

- `CLAUDE.md` is allowed and is the same one given to B and C (per the
  brief — the convention trap is *meant* to be discovered).
- Plan Mode is the only "ceremony" Plan Mode gets. Don't compensate by
  doing manual `/init`, breaking the task into substeps, or prompting
  Claude to "read the codebase first". The point is to measure the
  out-of-the-box behaviour.
