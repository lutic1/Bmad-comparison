<!--
SYNC IMPACT REPORT
Version change: N/A (template placeholders) → 1.0.0
Added sections:
  - Core Principles (7 principles derived from user-supplied body)
  - Governance
Modified principles: N/A (initial ratification)
Templates checked:
  - .specify/templates/plan-template.md ✅ Constitution Check section is generic; no update required
  - .specify/templates/spec-template.md ✅ No constitution-specific references
  - .specify/templates/tasks-template.md ✅ No constitution-specific references
Deferred TODOs: none
-->

# FastAPI Service Constitution

## Core Principles

### I. Technology Stack

Stack: Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest.

### II. Idiomatic FastAPI

Idiomatic FastAPI: small route functions, Pydantic models for
request and response shapes, dependency injection via Depends.

### III. Testing (NON-NEGOTIABLE)

Tests are non-optional. Minimum 80% line coverage on changed files.
Every new route ships with happy-path and at least one error-path
test.

### IV. Conventional Commits

Conventional commits: feat:, fix:, refactor:, test:, docs:, chore:.

### V. Dependency Management

No new third-party dependencies without a stated justification.

### VI. Type Safety

Type hints on every public function and route handler.

### VII. Focused Changes

Don't refactor unrelated code in the same change.

## Governance

This constitution supersedes all other practices for this project.
Amendments MUST increment the version (MAJOR: principle removal/redefinition;
MINOR: new principle added; PATCH: clarifications/wording). All pull requests
MUST pass a Constitution Check before merge. Compliance is reviewed on every
code review.

**Version**: 1.0.0 | **Ratified**: 2026-05-19 | **Last Amended**: 2026-05-19
