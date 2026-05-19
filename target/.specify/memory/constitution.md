<!--
Sync Impact Report
==================
Version change: (initial placeholder) → 1.0.0
Bump rationale: First concrete ratification; replaces template placeholders with
project-supplied governance content. MAJOR (1.0.0) because all placeholder
principles are being defined for the first time.

Modified principles: n/a (initial ratification — all content newly supplied)
Added sections:
  - Project constitution (verbatim body supplied by user)
Removed sections:
  - Placeholder Core Principles / [SECTION_2_NAME] / [SECTION_3_NAME] / Governance
    template scaffolding (replaced by verbatim user-supplied body)

Templates requiring updates:
  - .specify/templates/plan-template.md       ✅ no change needed (Constitution
    Check section references constitution generically; no hardcoded principles)
  - .specify/templates/spec-template.md       ✅ no change needed
  - .specify/templates/tasks-template.md      ✅ no change needed
  - .specify/templates/checklist-template.md  ✅ no change needed

Follow-up TODOs: none. Body is intentionally verbatim per user instruction;
section-heading scaffolding from the original template was omitted by explicit
request ("do not modify or expand it").
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
