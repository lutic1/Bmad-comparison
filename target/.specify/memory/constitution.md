<!--
SYNC IMPACT REPORT
==================
Version change: [template] → 1.0.0 (initial ratification)

Principles added:
  - I. Stack
  - II. Idiomatic FastAPI
  - III. Testing (Non-Negotiable)
  - IV. Conventional Commits
  - V. Dependencies
  - VI. Type Hints
  - VII. Refactoring Scope

Sections added: Core Principles, Governance
Sections removed: [SECTION_2_NAME], [SECTION_3_NAME] (not applicable to this project)

Templates reviewed:
  ✅ .specify/templates/plan-template.md — Constitution Check section is generic; no update needed
  ✅ .specify/templates/spec-template.md — no constitution references; no update needed
  ✅ .specify/templates/tasks-template.md — no constitution references; no update needed
  ✅ .specify/templates/checklist-template.md — not reviewed (no constitution references expected)

Deferred items: none
-->

# FastAPI Service Constitution

## Core Principles

### I. Stack

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

### V. Dependencies

No new third-party dependencies without a stated justification.

### VI. Type Hints

Type hints on every public function and route handler.

### VII. Refactoring Scope

Don't refactor unrelated code in the same change.

## Governance

This constitution supersedes all other practices. Amendments require
documentation and a version increment following semantic versioning:

- MAJOR: backward-incompatible principle removals or redefinitions.
- MINOR: new principle or section added, or materially expanded guidance.
- PATCH: clarifications, wording fixes, non-semantic refinements.

All PRs must verify compliance with the principles above before merge.

**Version**: 1.0.0 | **Ratified**: 2026-05-18 | **Last Amended**: 2026-05-18
