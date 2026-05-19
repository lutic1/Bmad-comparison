# Workflow C — BMAD

BMAD ("Breakthrough Method for Agile AI-Driven Development") drives the
agent through a set of personas with explicit handoffs: Analyst → PM →
Architect → PO → SM → Dev → QA. It also has a "Scale-Adaptive" setting
that lets smaller tasks skip personas, and a "Party Mode" for
multi-persona brainstorming.

## One-time setup

```bash
# Install BMAD per its docs (https://github.com/bmad-code-org/BMAD-METHOD).
# Typically a global npm install plus a per-project init that drops
# slash commands and agent files into the project.

npx bmad-method install   # follow prompts; install into the target/ directory
```

After installing inside `target/` you should have `/analyst`, `/pm`,
`/architect`, `/po`, `/sm`, `/dev`, `/qa`, `/party-mode` available in
Claude Code.

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

| Task | Scale setting | Notes |
| ---- | ------------- | ----- |
| 1    | Scale-Adaptive: **minimal** (Dev → QA only) | A one-file bugfix doesn't warrant Analyst/PM ceremony. Running full ceremony here would be unrealistic; running minimal here is the realistic BMAD configuration for trivial work. |
| 2    | Scale-Adaptive: **standard** (PM → Architect → SM → Dev → QA) | Well-specified medium task. Skip Analyst — there's nothing to elicit. |
| 3    | **Full ceremony** (Analyst → PM → Architect → PO → SM → Dev → QA) | The whole point of task 3 is requirements ambiguity. Use every persona. |
| 4    | Standard ceremony, **plus Party Mode between Architect and Dev** | The convention-discovery moment. Party Mode invites multiple personas to inspect the codebase together; this is BMAD's prescribed move for brownfield understanding. |

## Per-persona handoff prompts

Use the prompts below verbatim. They are deliberately neutral — they do
not pre-feed the task's acceptance criteria into any persona.

### `/analyst` (tasks 3 and 4)

```
We have a new request: <paste the task prompt verbatim>.
Elicit any missing requirements you need. Produce a brief that the PM
can use. When you have what you need, hand off to /pm.
```

### `/pm`

```
Take the Analyst's brief (or the raw request below if no Analyst was
involved: <paste task prompt>). Produce a PRD: goals, non-goals,
acceptance criteria, open questions. Hand off to /architect.
```

### `/architect`

```
Take the PRD. Produce a technical design that fits the existing
codebase. Read the relevant code first. Identify which files change
and how. Hand off to /po.
```

### `/party-mode` (task 4 only, between Architect and Dev)

```
Convention sweep. We have a small brownfield service and we are about
to implement <one-line summary of the architect's design>. Multiple
personas: read the codebase and surface every implicit convention or
gotcha the Dev needs to respect, especially around shared types,
units, and storage formats. Produce a short numbered list.
```

### `/po`

```
Take the architect's design. Slice it into stories the SM can pick up.
Verify each story has clear acceptance criteria. Hand off to /sm.
```

### `/sm`

```
Sequence the stories. For each, write a one-paragraph "ready for dev"
brief. Hand off to /dev.
```

### `/dev`

```
Implement the stories in order. Run pytest after each. Do not skip
tests. Hand off to /qa when done.
```

### `/qa`

```
Review the diff. Run pytest. If anything is broken or out of scope,
file findings back to /dev. Otherwise approve.
```

## When done

- Sanity check: `pytest` in `target/`.
- Sum token / cost across every persona invocation. Claude Code's
  `/cost` aggregates across the session, so a single `/cost` at the
  end is fine.
- Exit Claude Code.

Back in the harness:

- Confirm completion.
- Paste token / cost.
- Score using the rubric.
- For task 3, note how many requirements bullets the Analyst surfaced.
- For task 4, note whether Party Mode surfaced the integer-cents
  convention.

## Cleanup between runs

```bash
rm -f target/app.db
# BMAD drops files into target/docs/ and target/bmad-core/. They're
# part of the diff and the harness's branch reset handles them.
```

## Notes on this workflow

- Don't compress handoffs. The whole point of BMAD is the persona
  separation — feeding all the context to `/dev` at once would
  measure a different workflow.
- If a persona produces a deliverable that looks weak, do not iterate
  with it. Hand off and let the next persona deal with it. That's the
  realistic BMAD experience.
