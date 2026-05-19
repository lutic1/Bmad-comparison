<!--
Sync Impact Report
Version change: none (initial template) → 1.0.0
Modified principles: all placeholders replaced with concrete content
Added sections:
  - I. Stack
  - II. Idiomatic FastAPI
  - III. Testing (NON-NEGOTIABLE)
  - IV. Conventional Commits
  - V. Dependencies
  - VI. Type Hints
  - VII. Change Discipline
Removed sections: [SECTION_2_NAME], [SECTION_3_NAME] (subsumed into expanded principle set)
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no changes needed (Constitution Check is generic)
  - .specify/templates/spec-template.md ✅ no changes needed
  - .specify/templates/tasks-template.md ✅ no changes needed
Follow-up TODOs: none
-->

# FastAPI Service Constitution

## Core Principles

### I. Stack

Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest.

### II. Idiomatic FastAPI

Small route functions, Pydantic models for request and response shapes,
dependency injection via Depends.

### III. Testing (NON-NEGOTIABLE)

Tests are non-optional. Minimum 80% line coverage on changed files.
Every new route MUST ship with at least one happy-path test and at least
one error-path test.

### IV. Conventional Commits

Commit messages MUST use conventional commit prefixes: `feat:`, `fix:`,
`refactor:`, `test:`, `docs:`, `chore:`.

### V. Dependencies

No new third-party dependencies without a stated justification.

### VI. Type Hints

Type hints MUST appear on every public function and route handler.

### VII. Change Discipline

Don't refactor unrelated code in the same change.

## Governance

This constitution supersedes all other development practices. Amendments
require a documented rationale and a version bump following semantic
versioning:

- MAJOR: backward-incompatible principle removals or redefinitions.
- MINOR: new principle or section added.
- PATCH: clarifications, wording fixes, non-semantic refinements.

All pull requests MUST pass the Constitution Check in the implementation
plan before merging. Compliance is verified during code review.

**Version**: 1.0.0 | **Ratified**: 2026-05-18 | **Last Amended**: 2026-05-18
