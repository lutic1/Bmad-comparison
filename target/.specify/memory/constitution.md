<!--
Sync Impact Report:
Version change: (none) → 1.0.0
Added sections: Core Principles (7 principles), Governance
Modified principles: N/A (initial population from blank template)
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no changes required (Constitution Check section present)
  - .specify/templates/spec-template.md ✅ no changes required
  - .specify/templates/tasks-template.md ✅ no changes required
Follow-up TODOs: None
-->

# Benchmark-Target Constitution

## Core Principles

### I. Stack

Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest.

### II. API Design

Idiomatic FastAPI: small route functions, Pydantic models for
request and response shapes, dependency injection via Depends.

### III. Testing (NON-NEGOTIABLE)

Tests are non-optional. Minimum 80% line coverage on changed files.
Every new route ships with happy-path and at least one error-path
test.

### IV. Commit Convention

Conventional commits: feat:, fix:, refactor:, test:, docs:, chore:.

### V. Dependencies

No new third-party dependencies without a stated justification.

### VI. Type Safety

Type hints on every public function and route handler.

### VII. Scope Discipline

Don't refactor unrelated code in the same change.

## Governance

This constitution supersedes all other development practices.
Amendments MUST be documented with a version bump, rationale, and
reflected across dependent templates. All PRs MUST verify compliance
with the principles above before merging.

**Version**: 1.0.0 | **Ratified**: 2026-05-18 | **Last Amended**: 2026-05-18
