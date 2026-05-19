<!--
Sync Impact Report
Version change: N/A (initial template) → 1.0.0
Added sections: Core Principles (7 principles), Governance
Removed sections: [SECTION_2_NAME], [SECTION_3_NAME] (no content applicable to this project)
Templates requiring updates:
  - .specify/templates/plan-template.md: Constitution Check section already present ✅ (no changes required)
  - .specify/templates/spec-template.md: No constitution-specific sections affected ✅
  - .specify/templates/tasks-template.md: Test tasks align with Testing principle (Principle III) ✅
  - No command files found under .specify/templates/commands/
Follow-up TODOs: None — all placeholders resolved.
-->

# benchmark-target Constitution

## Core Principles

### I. Technology Stack

- Stack: Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest.

### II. API Design

- Idiomatic FastAPI: small route functions, Pydantic models for
  request and response shapes, dependency injection via Depends.

### III. Testing (NON-NEGOTIABLE)

- Tests are non-optional. Minimum 80% line coverage on changed files.
  Every new route ships with happy-path and at least one error-path
  test.

### IV. Commit Standards

- Conventional commits: feat:, fix:, refactor:, test:, docs:, chore:.

### V. Dependency Management

- No new third-party dependencies without a stated justification.

### VI. Type Safety

- Type hints on every public function and route handler.

### VII. Change Discipline

- Don't refactor unrelated code in the same change.

## Governance

This constitution supersedes all other practices. Amendments MUST update
this file, increment the version per semantic versioning (MAJOR: principle
removal/redefinition; MINOR: new principle added; PATCH: wording/typo),
and record the LAST_AMENDED_DATE. All implementation plans MUST include a
Constitution Check gate before Phase 0 research and re-check after Phase 1
design.

**Version**: 1.0.0 | **Ratified**: 2026-05-19 | **Last Amended**: 2026-05-19
