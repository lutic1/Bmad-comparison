<!--
Sync Impact Report
==================
Version change: (initial) → 1.0.0
Modified principles: N/A (initial ratification)
Added sections:
  - Core Principles (I–VII)
  - Governance
Removed sections: none
Templates requiring updates:
  - ✅ .specify/templates/plan-template.md (Constitution Check gate references current principles; no edits required)
  - ✅ .specify/templates/spec-template.md (no principle-specific sections; no edits required)
  - ✅ .specify/templates/tasks-template.md (test discipline aligns with Principle III; no edits required)
Follow-up TODOs: none
-->

# Project Constitution

## Core Principles

### I. Stack

Stack: Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest.

### II. Idiomatic FastAPI

Idiomatic FastAPI: small route functions, Pydantic models for
request and response shapes, dependency injection via Depends.

### III. Tests Are Non-Optional

Tests are non-optional. Minimum 80% line coverage on changed files.
Every new route ships with happy-path and at least one error-path
test.

### IV. Conventional Commits

Conventional commits: feat:, fix:, refactor:, test:, docs:, chore:.

### V. Dependency Discipline

No new third-party dependencies without a stated justification.

### VI. Type Hints

Type hints on every public function and route handler.

### VII. Focused Changes

Don't refactor unrelated code in the same change.

## Governance

This constitution supersedes ad-hoc practice for the repository. Amendments require a
pull request that updates this file, bumps the version per the policy below, and
updates the Sync Impact Report.

Versioning policy (semantic):
- MAJOR: backward-incompatible governance or principle removals/redefinitions.
- MINOR: a new principle or section, or materially expanded guidance.
- PATCH: clarifications, wording, or non-semantic refinements.

Compliance: every PR is expected to comply with the principles above. Deviations
must be called out explicitly in the PR description and justified.

**Version**: 1.0.0 | **Ratified**: 2026-05-19 | **Last Amended**: 2026-05-19
