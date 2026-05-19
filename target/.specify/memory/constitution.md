<!--
Sync Impact Report
- Version change: 0.0.0 → 1.0.0 (initial ratification from template)
- Modified principles: N/A (template placeholders replaced with first concrete content)
- Added sections: Core constitution body (flat bullet list as supplied verbatim by ratifier)
- Removed sections: Template placeholder sections (PRINCIPLE_1..5, SECTION_2/3, Governance placeholder)
- Templates requiring updates:
  - ✅ .specify/templates/plan-template.md (Constitution Check gate references current file; no rewording needed)
  - ✅ .specify/templates/spec-template.md (no constitution-derived sections impacted)
  - ✅ .specify/templates/tasks-template.md (test discipline already aligns with "tests are non-optional")
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
