# Workflow C — BMAD

BMAD ("Breakthrough Method for Agile AI-Driven Development") drives the
agent through a set of personas with explicit handoffs. The v6 line
ships these as Claude Code **skills**, not slash commands. The persona
list also changed: there is no explicit `/po`, `/sm`, or `/qa` skill
anymore — their responsibilities are absorbed into purpose-specific
skills (`bmad-check-implementation-readiness`, `bmad-create-story`,
`bmad-code-review`). This runbook uses the v6.7.1 mapping.

## One-time setup

```bash
# Install BMAD v6 into the target directory. Non-interactive form:
npx --yes bmad-method install \
  --directory target \
  --modules bmm \
  --tools claude-code \
  --yes \
  --all-stable
```

After install you should see:

- `target/.claude/skills/bmad-*` — 44 skills including the agents below
- `target/_bmad/` — module config and shared scripts
- `target/_bmad-output/` — where BMAD writes planning + implementation
  artifacts during a run

In this benchmark the install is committed once on the `bmad-base`
branch; the harness branches every `workflow-c/*` run off that, so the
install is inherited and you do not need to re-run `npx bmad-method
install` per run.

## v6.7.1 persona → skill mapping

The runbook below uses these skill names. Original BMAD role on the
left, the skill the operator actually invokes on the right:

| Role          | Skill (v6.7.1)                       |
| ------------- | ------------------------------------ |
| Analyst       | `bmad-agent-analyst`                 |
| PM            | `bmad-agent-pm`                      |
| Architect     | `bmad-agent-architect`               |
| PO            | `bmad-check-implementation-readiness`|
| SM            | `bmad-create-story`                  |
| Dev           | `bmad-agent-dev`                     |
| QA            | `bmad-code-review` (default)         |
| Party Mode    | `bmad-party-mode`                    |

Optional: substitute `bmad-review-adversarial-general` for QA on tasks
where stress-testing is explicitly desired. Note the substitution in
the run's `notes` column if you do. The baseline is `bmad-code-review`.

To invoke a skill inside Claude Code, use the Skill tool / `/skill`
mechanism per your Claude Code version, naming the skill exactly as it
appears in `target/.claude/skills/`.

## Per-run procedure

```bash
python harness/run.py --workflow c --task <N> --run <M>
```

When the harness pauses, in another shell:

```bash
cp workflows/claude-md-template/CLAUDE.md target/CLAUDE.md
cd target
claude
```

Pick the scale setting per task:

| Task | Scale setting | Skills used |
| ---- | ------------- | ----------- |
| 1    | Scale-Adaptive: **minimal** | `bmad-agent-dev` → `bmad-code-review` |
| 2    | Scale-Adaptive: **standard** | `bmad-agent-pm` → `bmad-agent-architect` → `bmad-create-story` → `bmad-agent-dev` → `bmad-code-review` |
| 3    | **Full ceremony** | `bmad-agent-analyst` → `bmad-agent-pm` → `bmad-agent-architect` → `bmad-check-implementation-readiness` → `bmad-create-story` → `bmad-agent-dev` → `bmad-code-review` |
| 4    | Standard + **Party Mode between Architect and Dev** | `bmad-agent-pm` → `bmad-agent-architect` → `bmad-party-mode` → `bmad-create-story` → `bmad-agent-dev` → `bmad-code-review` |

Rationale: task 1 is a one-file bugfix, so full ceremony is unrealistic.
Task 2 is well-specified, so skip the Analyst. Task 3 is the
ambiguity-draining task, so use everyone. Task 4 is the convention-trap
brownfield task, so insert Party Mode after Architect for the codebase
sweep.

## Per-persona handoff prompts

Use the prompts below verbatim. They are deliberately neutral — they do
not pre-feed the task's acceptance criteria into any skill.

### `bmad-agent-analyst` (tasks 3 and 4)

```
We have a new request: <paste the task prompt verbatim>.
Elicit any missing requirements you need. Produce a brief that the PM
can use. When you have what you need, hand off to bmad-agent-pm.
```

### `bmad-agent-pm`

```
Take the Analyst's brief (or the raw request below if no Analyst was
involved: <paste task prompt>). Produce a PRD: goals, non-goals,
acceptance criteria, open questions. Hand off to bmad-agent-architect.
```

### `bmad-agent-architect`

```
Take the PRD. Produce a technical design that fits the existing
codebase. Read the relevant code first. Identify which files change
and how. Hand off to bmad-check-implementation-readiness.
```

### `bmad-party-mode` (task 4 only, between Architect and Story creation)

```
Convention sweep. We have a small brownfield service and we are about
to implement <one-line summary of the architect's design>. Multiple
personas: read the codebase and surface every implicit convention or
gotcha the Dev needs to respect, especially around shared types,
units, and storage formats. Produce a short numbered list.
```

### `bmad-check-implementation-readiness` (PO equivalent)

```
Take the architect's design. Verify each piece of work has clear
acceptance criteria and is ready to be sliced into stories. Flag any
gaps back to bmad-agent-architect. When green, hand off to
bmad-create-story.
```

### `bmad-create-story` (SM equivalent)

```
Sequence the work into stories. For each, write a one-paragraph
"ready for dev" brief with acceptance criteria. Hand off to
bmad-agent-dev.
```

### `bmad-agent-dev`

```
Implement the stories in order. Run pytest after each. Do not skip
tests. Hand off to bmad-code-review when done.
```

### `bmad-code-review` (QA equivalent)

```
Review the diff. Run pytest. If anything is broken or out of scope,
file findings back to bmad-agent-dev. Otherwise approve.
```

## When done

- Sanity check: `pytest` in `target/`.
- Sum token / cost across every skill invocation. Claude Code's
  `/cost` aggregates across the session, so a single `/cost` at the
  end is fine.
- Exit Claude Code.

Back in the harness:

- Confirm completion.
- Paste token / cost.
- Score using the rubric.
- For task 3, note how many requirements bullets the Analyst surfaced.
- For task 4, note whether Party Mode surfaced the integer-cents
  convention. Use the phrasing the README mandates:
  `convention discovered: yes/no — evidence: <X>`.

## Cleanup between runs

```bash
rm -f target/app.db
# BMAD writes generated artifacts to target/_bmad-output/. They're
# part of the diff and the harness's branch reset handles them when it
# checks out bmad-base for the next workflow-c run.
```

## Notes on this workflow

- Don't compress handoffs. The whole point of BMAD is the persona
  separation — feeding all the context to `bmad-agent-dev` at once
  would measure a different workflow.
- If a skill produces a deliverable that looks weak, do not iterate
  with it. Hand off and let the next skill deal with it. That's the
  realistic BMAD experience.
- The v6.7.1 mapping (`bmad-check-implementation-readiness` for PO,
  `bmad-create-story` for SM, `bmad-code-review` for QA) is a runbook
  decision, not something BMAD prescribes. If a future BMAD release
  ships explicit `bmad-agent-po` / `bmad-agent-sm` / `bmad-agent-qa`
  skills, prefer those and update this file.
