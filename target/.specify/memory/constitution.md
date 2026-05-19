<!--
Sync Impact Report
==================
Version change: (none) → 1.0.0 (initial population from blank template)
Modified principles: all placeholder tokens replaced
Added sections: Core Principles (7 principles), Governance
Removed sections: [SECTION_2_NAME], [SECTION_3_NAME] (not applicable to this constitution)
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no constitution-specific references require change
  - .specify/templates/spec-template.md ✅ no constitution-specific references require change
  - .specify/templates/tasks-template.md ✅ no constitution-specific references require change
Follow-up TODOs: None
-->

# benchmark-target Constitution

## Core Principles

### I. Stack

- Stack: Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest.

### II. Idiomatic FastAPI

- Idiomatic FastAPI: small route functions, Pydantic models for
  request and response shapes, dependency injection via Depends.

### III. Testing

- Tests are non-optional. Minimum 80% line coverage on changed files.
  Every new route ships with happy-path and at least one error-path
  test.

### IV. Conventional Commits

- Conventional commits: feat:, fix:, refactor:, test:, docs:, chore:.

### V. Dependencies

- No new third-party dependencies without a stated justification.

### VI. Type Hints

- Type hints on every public function and route handler.

### VII. Focused Changes

- Don't refactor unrelated code in the same change.

## Governance

This constitution supersedes all other project guidelines. Amendments require a documented rationale and a version bump following semantic versioning:

- MAJOR: backward-incompatible principle removal or redefinition.
- MINOR: new principle or section added.
- PATCH: wording clarifications or non-semantic refinements.

All PRs must verify compliance with the principles above before merge.

**Version**: 1.0.0 | **Ratified**: 2026-05-18 | **Last Amended**: 2026-05-18
