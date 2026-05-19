<!--
Sync Impact Report
==================
Version change: [template] → 1.0.0
Bump rationale: MINOR — initial constitution populated from template placeholders.

Modified principles: N/A (first population, no prior principles)
Added sections: Core Principles (verbatim body), Governance
Removed sections: SECTION_2, SECTION_3 (merged into flat principle list per user input)

Templates checked:
  ✅ .specify/templates/plan-template.md — Constitution Check gate references constitution generically; no stale content.
  ✅ .specify/templates/spec-template.md — No direct constitution references; aligned.
  ⚠  .specify/templates/tasks-template.md — Line 12 states "Tests are OPTIONAL" which conflicts with the constitution
     principle "Tests are non-optional." Manual update to tasks-template.md recommended to align with this constitution.
  ✅ .specify/templates/constitution-template.md — Source template; no update needed.

Deferred TODOs: none.
-->

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

## Governance

This constitution supersedes all other documented practices. Amendments MUST be
proposed with a rationale and recorded as a version bump. Semantic versioning
applies: MAJOR for principle removals or redefinitions, MINOR for additions,
PATCH for clarifications or wording fixes. All PRs MUST verify compliance with
the principles above before merging.

**Version**: 1.0.0 | **Ratified**: 2026-05-19 | **Last Amended**: 2026-05-19
