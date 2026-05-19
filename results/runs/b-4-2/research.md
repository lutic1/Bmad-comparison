# Research: Discount Codes at Checkout

## Decision Log

### 1. Discount Code Storage

**Decision**: New `DiscountCode` SQLAlchemy model backed by a DB table, seeded
at startup.

**Rationale**: A table is consistent with the project's use of SQLAlchemy for
all persistent data. It allows operator management without code changes and
supports future additions (expiry, usage limits) without schema explosions.
Hard-coded constants would require a code deploy to add/remove codes.

**Alternatives considered**:
- Hard-coded dict in routes — rejected; not operator-manageable, violates
  Single Responsibility.
- Environment variable list — rejected; not queryable; harder to extend.

---

### 2. Case-Insensitive Lookup

**Decision**: Normalise all discount codes to uppercase on write (seed) and on
read (user submission). No collation change to the SQLite column.

**Rationale**: Application-level normalisation is portable, works with SQLite's
default collation, and keeps the query simple (`WHERE code = :code` after
uppercasing in Python). FR-007 is satisfied without a DB-level COLLATE clause.

**Alternatives considered**:
- SQLite `COLLATE NOCASE` column — works but ties the approach to SQLite.
- `LOWER()` in query — equivalent; uppercase chosen because code names
  (`SAVE10`) are conventionally uppercase.

---

### 3. Applying Discount to Order Total

**Decision**: `Order.total` stores the **post-discount** final amount in cents.
A new nullable `Order.discount_code` string column records the applied code.

**Rationale**: The existing response shape exposes `total` as "what the user
pays". Keeping `total` as the final amount requires no change to downstream
consumers. The spec (FR-005) requires recording the code and the discounted
total; this satisfies both in the fewest added columns.

**Alternatives considered**:
- Store gross and discounted total as separate columns — adds a column with
  no requirement driving it; YAGNI.
- Compute discount at read time from items — cannot guarantee accuracy if
  items are later modified; fragile.

---

### 4. Seeding Discount Codes

**Decision**: Seed codes (`SAVE5`/`SAVE10`/`SAVE20`) in the FastAPI `lifespan`
function in `main.py` using an `INSERT OR IGNORE` pattern (upsert by code).

**Rationale**: Consistent with existing table-creation in the same lifespan
block. Tests override the DB dependency via conftest; the seed function is
called in the test engine's `create_all` path through a helper so test clients
also have codes available.

**Alternatives considered**:
- Alembic migration with seeding — no migrations in this project; ruled out.
- Separate seed script — introduces ops complexity for a small service.

---

### 5. Validation Error Shape

**Decision**: Return HTTP 422 Unprocessable Entity with a descriptive JSON
`detail` when an unrecognised discount code is submitted.

**Rationale**: 422 is the FastAPI/HTTP convention for business-rule validation
failures that pass schema validation (the code string is syntactically valid but
semantically rejected). Consistent with how FastAPI itself signals invalid data.

**Alternatives considered**:
- 400 Bad Request — less precise; 400 conventionally means malformed input, not
  an unrecognised business value.
- 404 Not Found — semantically wrong; the *order* is not being fetched.
