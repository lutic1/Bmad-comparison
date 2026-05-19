<!-- SYNC IMPACT REPORT
Version: 0.0.0 → 1.0.0
Type: MINOR (initial ratification — constitution filled from blank template)
Modified Principles: N/A (fresh constitution, no prior principles)
Added Sections: Core Principles (7 bullet points), Governance
Removed Sections: N/A
Templates requiring updates:
  - .specify/templates/tasks-template.md ✅ updated — "Tests are OPTIONAL" language
    replaced to align with "Tests are non-optional" constitution principle
  - .specify/templates/plan-template.md ✅ no changes required
  - .specify/templates/spec-template.md ✅ no changes required
Deferred TODOs: None
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

Amendments MUST be documented with a version bump following semantic versioning
(MAJOR: breaking principle removal or redefinition; MINOR: new principle or
material expansion; PATCH: clarification or wording fix). All PRs MUST pass a
Constitution Check gate as defined in the plan template before merging.
This constitution supersedes all other project guidance documents.

**Version**: 1.0.0 | **Ratified**: 2026-05-19 | **Last Amended**: 2026-05-19
