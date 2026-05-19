<!--
SYNC IMPACT REPORT
==================
Version change: (template) → 1.0.0 (initial population)

Added principles:
  - I. Technology Stack (new)
  - II. API Design (new)
  - III. Testing (new)
  - IV. Commit Conventions (new)
  - V. Dependency Discipline (new)
  - VI. Type Safety (new)
  - VII. Scope Discipline (new)

Removed sections: N/A (template placeholders replaced)

Templates reviewed:
  ✅ .specify/templates/plan-template.md — Constitution Check section references
     "constitution file" generically; no updates required.
  ✅ .specify/templates/spec-template.md — no constitution-specific references.
  ✅ .specify/templates/tasks-template.md — test tasks already structured
     consistently with Principle III (tests non-optional, per-story coverage).

Follow-up TODOs:
  - RATIFICATION_DATE set to 2026-05-19 (today); update if an earlier adoption
    date is known.
-->

# benchmark-target Constitution

## Core Principles

### I. Technology Stack

Stack: Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest.

### II. API Design

Idiomatic FastAPI: small route functions, Pydantic models for
request and response shapes, dependency injection via Depends.

### III. Testing

Tests are non-optional. Minimum 80% line coverage on changed files.
Every new route ships with happy-path and at least one error-path
test.

### IV. Commit Conventions

Conventional commits: feat:, fix:, refactor:, test:, docs:, chore:.

### V. Dependency Discipline

No new third-party dependencies without a stated justification.

### VI. Type Safety

Type hints on every public function and route handler.

### VII. Scope Discipline

Don't refactor unrelated code in the same change.

## Governance

This constitution supersedes all other documented practices. Amendments
MUST increment the version following semantic versioning:

- MAJOR: backward-incompatible principle removal or redefinition.
- MINOR: new principle added or materially expanded.
- PATCH: clarifications, wording fixes, non-semantic refinements.

All pull requests MUST pass a Constitution Check (see plan-template.md)
before merging. Any deliberate violation MUST be justified in the
Complexity Tracking table of the relevant plan.md.

**Version**: 1.0.0 | **Ratified**: 2026-05-19 | **Last Amended**: 2026-05-19
