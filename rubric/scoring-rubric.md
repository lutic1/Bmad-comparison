# Scoring rubric

A single 1–5 score per run, awarded by the operator after reading the
final diff and the test results. Anchors are concrete so scoring stays
consistent across all 36 runs.

| Score | Meaning | Concrete anchor — would you... |
| ----- | ------- | ------------------------------ |
| **5** | **Merge as-is.** | …click "merge" without further comment. Diff is clean, idiomatic, all tests pass, no over-engineering, respects existing conventions (including integer cents, X-User-Id auth, route file layout). |
| **4** | **Merge after trivial review comments.** | …leave one or two non-blocking comments (a missing docstring, a slightly-off variable name, a redundant test) and then merge. The work itself is right. |
| **3** | **Request changes.** | …leave substantive review comments and ask for another round. Functional but at least one of: scope creep ("why are we touching `users.py` here?"), missing edge case the spec implied, an awkward pattern that doesn't match the codebase, a flaky-looking test. |
| **2** | **Significant rework needed.** | …reply "this needs a rethink" or "let's pair on this". Functional in the happy case but architecturally wrong, or contains a real bug (off-by-one, lost data, breaks an existing invariant) you can point at concretely. |
| **1** | **Reject.** | …close the PR. Doesn't work, hallucinated APIs (used a library not in `pyproject.toml`, called a function that doesn't exist), breaks existing tests, or is so over-engineered (new abstractions, plugin systems, config layers for one call site) that reviewing it is unreasonable. |

## Tiebreakers

When a run is between two scores, drop to the lower score if **any** of
these is true:

- An existing test was broken or deleted to make the diff "pass". (→ 1)
- A new third-party dependency was added without need. (→ −1)
- The diff touches files unrelated to the task. (→ −1)
- For task 4: the integer-cents convention was violated (a `Float`
  column added for money, or a stored total of `899.5`, or a response
  that returns dollars-as-float for one endpoint and cents elsewhere).
  (→ at most 2)

Bump up by one only if the diff demonstrably **improves on what the
task asked**: e.g. for task 3, the workflow not only implements rate
limiting but documents the choice in a comment or a short docstring
that a reviewer would value.

## Operator discipline

- Score from the diff and the test output, not from how impressive
  the agent's narration felt during the run.
- Don't peek at the workflow column before scoring. (In practice this
  is hard with one operator — but at least read the diff before you
  remind yourself which workflow produced it.)
- Write one sentence in `notes` explaining the score. "3 — added a
  refund endpoint but also rewrote users.py for no reason." That
  sentence is what you'll thank yourself for when writing the article.
