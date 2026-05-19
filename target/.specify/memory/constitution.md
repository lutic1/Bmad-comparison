<!--
Sync Impact Report:
- Version change: (none) → 1.0.0 (initial ratification from template)
- Added sections: Core Principles (7 principles), Governance
- Removed sections: Section 2, Section 3 (no content provided in constitution body)
- Templates reviewed:
  - .specify/templates/plan-template.md ✅ (Constitution Check section is generic; no update needed)
  - .specify/templates/spec-template.md ✅ (requirements structure aligned with principles; no update needed)
  - .specify/templates/tasks-template.md ✅ (task phases and test discipline align with testing principle; no update needed)
- No deferred TODOs
-->

# benchmark-target Constitution

## Core Principles

### I. Technology Stack

Stack: Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest.

### II. API Design

Idiomatic FastAPI: small route functions, Pydantic models for
request and response shapes, dependency injection via Depends.

### III. Testing (NON-NEGOTIABLE)

Tests are non-optional. Minimum 80% line coverage on changed files.
Every new route ships with happy-path and at least one error-path
test.

### IV. Commit Conventions

Conventional commits: feat:, fix:, refactor:, test:, docs:, chore:.

### V. Dependency Management

No new third-party dependencies without a stated justification.

### VI. Type Safety

Type hints on every public function and route handler.

### VII. Scope Discipline

Don't refactor unrelated code in the same change.

## Governance

This constitution supersedes all other practices. Amendments MUST be documented,
versioned using MAJOR.MINOR.PATCH semantic versioning, and reflected in this file.

- MAJOR: Backward-incompatible removal or redefinition of a principle.
- MINOR: New principle added or materially expanded.
- PATCH: Clarification, wording fix, or non-semantic refinement.

All PRs and reviews MUST verify compliance with the principles above.

**Version**: 1.0.0 | **Ratified**: 2026-05-19 | **Last Amended**: 2026-05-19
