<!--
SYNC IMPACT REPORT
Version change: N/A → 1.0.0 (initial ratification)
Added sections: Project constitution (7 principles), Governance
Removed sections: N/A (first version)
Templates requiring updates:
  ✅ .specify/memory/constitution.md (this file)
  ✅ .specify/templates/tasks-template.md — tests-are-OPTIONAL language updated to MANDATORY
  ✅ .specify/templates/plan-template.md — Constitution Check section already generic, no changes needed
  ✅ .specify/templates/spec-template.md — no structural changes needed
Deferred TODOs: None
-->

# Project Constitution

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

This constitution supersedes all other development practices for this project.
Amendments MUST be documented with a rationale, increment the version following
semantic versioning (MAJOR: principle removal/redefinition; MINOR: new principle
added; PATCH: clarification/wording), and update `LAST_AMENDED_DATE`. All PRs
MUST verify compliance. Violations MUST be justified in the plan's Complexity
Tracking section.

**Version**: 1.0.0 | **Ratified**: 2026-05-19 | **Last Amended**: 2026-05-19
