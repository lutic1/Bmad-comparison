<!--
Sync Impact Report
==================
Version change: (uninitialized template) → 1.0.0
Bump rationale: Initial ratification of the project constitution; the previous
file contained only template placeholders, so this is a MAJOR-equivalent
initialization (1.0.0).

Modified principles: none (initial adoption)
Added sections:
  - Core Principles (7 principles, verbatim from user input)
  - Governance
Removed sections:
  - [SECTION_2_NAME] / [SECTION_3_NAME] placeholders (not used; the
    project chose not to define optional sections at ratification)

Templates requiring updates:
  - ✅ .specify/templates/plan-template.md — Constitution Check gate is
    constitution-agnostic ("Gates determined based on constitution file");
    no change required.
  - ✅ .specify/templates/spec-template.md — no constitution-specific
    references; aligned.
  - ✅ .specify/templates/tasks-template.md — no constitution-specific
    references; aligned.
  - ✅ .specify/templates/checklist-template.md — no constitution-specific
    references; aligned.

Follow-up TODOs: none
-->

# Project Constitution

## Core Principles

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

## Governance

This constitution supersedes ad-hoc practices. Amendments MUST be made via
pull request with a documented rationale and a semantic version bump:
MAJOR for backward-incompatible principle removal or redefinition, MINOR
for added or materially expanded principles, PATCH for clarifications and
wording fixes. All PRs and reviews MUST verify compliance with the
principles above; deviations MUST be explicitly justified in the PR
description.

**Version**: 1.0.0 | **Ratified**: 2026-05-19 | **Last Amended**: 2026-05-19
