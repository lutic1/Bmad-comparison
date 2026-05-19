<!--
Sync Impact Report
==================
Version change: N/A (placeholder template) → 1.0.0 (initial ratification)

Modified principles: All placeholder tokens replaced with project-specific content
  - [PROJECT_NAME] → FastAPI Service
  - [PRINCIPLE_1_NAME/DESCRIPTION] → I. Technology Stack
  - [PRINCIPLE_2_NAME/DESCRIPTION] → II. Idiomatic API Design
  - [PRINCIPLE_3_NAME/DESCRIPTION] → III. Testing (NON-NEGOTIABLE)
  - [PRINCIPLE_4_NAME/DESCRIPTION] → IV. Commit Convention
  - [PRINCIPLE_5_NAME/DESCRIPTION] → V. Dependency Management
  - [SECTION_2_NAME/CONTENT] → VI. Type Safety (promoted to principle)
  - [SECTION_3_NAME/CONTENT] → VII. Change Scope (promoted to principle)
  - [GOVERNANCE_RULES] → Amendment and compliance rules
  - [RATIFICATION_DATE] → 2026-05-19
  - [LAST_AMENDED_DATE] → 2026-05-19

Added sections: 7 principles (2 beyond template default of 5)
Removed sections: None (extra template sections absorbed as principles VI and VII)

Templates requiring updates:
  ✅ .specify/templates/plan-template.md — Constitution Check gate is generic; no update needed
  ✅ .specify/templates/spec-template.md — No principle-specific references; no update needed
  ✅ .specify/templates/tasks-template.md — No principle-specific references; no update needed

Follow-up TODOs: None — all placeholders resolved
-->

# FastAPI Service Constitution

## Core Principles

### I. Technology Stack

Stack: Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest.

### II. Idiomatic API Design

Idiomatic FastAPI: small route functions, Pydantic models for
request and response shapes, dependency injection via Depends.

### III. Testing (NON-NEGOTIABLE)

Tests are non-optional. Minimum 80% line coverage on changed files.
Every new route ships with happy-path and at least one error-path
test.

### IV. Commit Convention

Conventional commits: feat:, fix:, refactor:, test:, docs:, chore:.

### V. Dependency Management

No new third-party dependencies without a stated justification.

### VI. Type Safety

Type hints on every public function and route handler.

### VII. Change Scope

Don't refactor unrelated code in the same change.

## Governance

This constitution supersedes all other practices. Amendments MUST be
documented with a version bump, a rationale, and recorded here.

Versioning policy:
- MAJOR: backward-incompatible principle removals or redefinitions.
- MINOR: new principle added or materially expanded guidance.
- PATCH: clarifications, wording fixes, or non-semantic refinements.

All PRs MUST verify compliance with these principles before merge.
Complexity exceptions MUST be documented in the plan's Complexity
Tracking table with a justification.

**Version**: 1.0.0 | **Ratified**: 2026-05-19 | **Last Amended**: 2026-05-19
