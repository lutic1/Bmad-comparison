<!--
SYNC IMPACT REPORT
==================
Version change: (uninitialized template) → 1.0.0
Rationale: Initial ratification — first concrete constitution adopted from the
template, so MAJOR bump from 0.0.0 placeholder state to 1.0.0.

Modified principles: N/A (initial adoption)
Added sections:
  - Project constitution (body provided verbatim by maintainer)
Removed sections:
  - Template placeholders (PROJECT_NAME, PRINCIPLE_1..5, SECTION_2, SECTION_3,
    GOVERNANCE_RULES) — replaced by the verbatim project body.

Note on structure: The maintainer supplied the constitution body verbatim with
an explicit instruction not to modify or expand it. The standard template's
"Core Principles" / "Governance" subheadings are therefore not used; the body
itself enumerates the binding rules.

Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no change required
    (Constitution Check gate is generic and resolves against this file)
  - .specify/templates/spec-template.md ✅ no change required
  - .specify/templates/tasks-template.md ✅ no change required
  - .specify/templates/checklist-template.md ✅ no change required

Follow-up TODOs: none.
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
