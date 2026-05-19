<!--
SYNC IMPACT REPORT
Version change: (none) → 1.0.0
Added sections: Core Principles, Governance
Modified principles: N/A (initial constitution)
Templates reviewed:
  .specify/templates/plan-template.md ✅ no changes required
  .specify/templates/spec-template.md ✅ no changes required
  .specify/templates/tasks-template.md ✅ updated: "Tests OPTIONAL" language replaced
    to reflect constitution mandate (tests are non-optional)
Deferred TODOs: none
-->

# FastAPI Service Constitution

## Core Principles

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

This constitution supersedes all other practices. Amendments MUST be
documented with a version bump following semantic versioning:

- MAJOR: backward-incompatible principle removals or redefinitions
- MINOR: new principle or section added
- PATCH: clarifications, wording, or non-semantic refinements

All PRs MUST pass a Constitution Check before merge.

**Version**: 1.0.0 | **Ratified**: 2026-05-18 | **Last Amended**: 2026-05-18
