# Project guardrails

This is a small FastAPI service (users + orders, SQLAlchemy + SQLite,
pytest). Below are the conventions to respect when making changes.

## Stack

- Python 3.11+, FastAPI, SQLAlchemy 2.x (declarative `Mapped[...]` style),
  Pydantic v2, pytest.
- The HTTP layer lives in `src/api/routes/`. Dependencies (`get_db`,
  `get_current_user`) are in `src/api/deps.py`. Models in
  `src/api/models.py`.

## Authentication

There is no real auth in this service. Endpoints that need a user accept
an `X-User-Id` header — see `api.deps.get_current_user`. New protected
endpoints should depend on the same helper rather than re-implementing
it.

## Testing

- Every change ships with tests. **Do not commit if `pytest` is failing.**
- Use the existing `client` fixture in `tests/conftest.py` for HTTP
  tests. It already wires an in-memory SQLite per test.
- Prefer covering one behaviour per test over one giant test.

## Code style

- Follow the patterns already in the repo: small route functions,
  Pydantic models for request/response shapes, business logic inline in
  the route when it's a few lines, factored out when it isn't.
- No new third-party dependencies without a clear reason. Stdlib first.
- Type hints on public functions and route handlers.

## Database

- SQLite via SQLAlchemy. Schema is created from `Base.metadata` at
  startup; there are no migrations. If you add or change a column,
  the operator will wipe `app.db` between runs — don't bother writing
  a migration.

<!-- SPECKIT START -->
## Active Feature Plan

Implementation plan: [specs/001-api-rate-limiting/plan.md](specs/001-api-rate-limiting/plan.md)
<!-- SPECKIT END -->

## What not to do

- Don't refactor unrelated code "while you're here".
- Don't introduce abstractions for a single call site.
- Don't add logging, metrics, tracing, or middleware unless the task
  asks for it.
- Don't change `pyproject.toml` lower bounds without a reason.
