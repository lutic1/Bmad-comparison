<!--
Sync Impact Report
- Version change: none → 1.0.0 (initial ratification)
- Modified principles: n/a (initial ratification; prior file was an unfilled template)
- Added sections: Project constitution (single body section, bulleted principles as provided by stakeholder)
- Removed sections: Core Principles / Section 2 / Section 3 / Governance placeholder scaffolding (replaced with the verbatim stakeholder body)
- Templates requiring updates:
  - ✅ .specify/templates/plan-template.md (Constitution Check gate remains generic; no changes required)
  - ✅ .specify/templates/spec-template.md (no constitution-specific references; no changes required)
  - ✅ .specify/templates/tasks-template.md (no constitution-specific references; no changes required)
  - ✅ .specify/templates/checklist-template.md (no constitution-specific references; no changes required)
- Follow-up TODOs: none
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

**Version**: 1.0.0 | **Ratified**: 2026-05-19 | **Last Amended**: 2026-05-19
