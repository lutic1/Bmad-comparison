---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-target-2026-05-19/prd.md
workflowType: architecture
project_name: target
user_name: Luisticas
date: 2026-05-19
---

# Architecture Decision Document — Discount Code at Checkout

_Generated 2026-05-19. Covers only the changes required by the PRD. Existing code that is not touched is not described here._

---

## 1. Context & Constraints

The service is a small FastAPI app (Python 3.11, SQLAlchemy 2.x declarative style, Pydantic v2, SQLite, pytest). All prices are stored as **integer cents** via a `_to_cents()` helper in `routes/orders.py`. There are no migrations — schema is rebuilt from `Base.metadata` at startup. The operator wipes `app.db` between deploys when the schema changes.

The feature adds one new table, two new nullable columns on `orders`, and a single new lookup call in `POST /orders`. No new endpoints, no new dependencies, no migrations.

---

## 2. Files That Change

| File | Change type | Summary |
|---|---|---|
| `src/api/models.py` | Add model + alter model | New `DiscountCode` class; two nullable columns on `Order` |
| `src/api/routes/orders.py` | Extend existing | `OrderCreate` + `OrderOut` schema fields; discount lookup + computation inline in `create_order`; `OrderOut` construction updated in both `create_order` and `get_order` |
| `tests/conftest.py` | Minimal addition | New `db` fixture (session over `db_engine`) — needed to seed `DiscountCode` rows in discount tests |
| `tests/test_discount.py` | New file | All discount-feature tests |

No other files change. `main.py`, `deps.py`, `users.py`, `utils/`, and the existing test files are untouched.

---

## 3. Data Model

### 3.1 New table: `discount_codes`

```python
# src/api/models.py

from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class DiscountCode(Base):
    __tablename__ = "discount_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    percentage: Mapped[int] = mapped_column(Integer, nullable=False)
```

- `unique=True` on `code` creates the database-level unique index required by FR-4 NFR.
- `percentage` is validated at the application layer (Pydantic / route logic), not via a `CheckConstraint`. SQLite silently ignores `CHECK` constraints in some older driver configurations; Pydantic validation is the reliable enforcement point for this codebase.
- No relationship back-reference to `Order` — there is no join needed at query time.

### 3.2 New columns on `Order`

```python
# src/api/models.py — Order class

discount_code: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
discounted_total: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
```

Both are nullable. Existing rows (and orders without a code) have `NULL` in both columns. `default=None` is explicit for clarity; SQLAlchemy treats nullable columns as `None` by default.

**Decision — null vs. omit in response (PRD Open Question #3):** Fields are always present in the JSON response, set to `null` when no discount was applied. This avoids `KeyError` in typed clients and is consistent with every other nullable field pattern in the service. Enforced by `str | None = None` / `int | None = None` in `OrderOut`.

---

## 4. Schema Changes (Pydantic)

### 4.1 `OrderCreate` — add optional field

```python
class OrderCreate(BaseModel):
    items: list[OrderItemIn]
    discount_code: str | None = None
```

Omitting the field is equivalent to `None` — no discount applied.

### 4.2 `OrderOut` — add two nullable response fields

```python
class OrderOut(BaseModel):
    id: int
    user_id: int
    total: int
    created_at: str
    items: list[OrderItemOut]
    discount_code: str | None = None
    discounted_total: int | None = None
```

Both fields default to `None` so existing call sites that build `OrderOut(...)` without the new kwargs continue to work until they are updated.

---

## 5. Route Logic

### 5.1 `create_order` — discount lookup and computation

The lookup and computation are ~6 lines and belong inline in the route, consistent with the codebase's stated convention ("business logic inline in the route when it's a few lines").

Placement: **after** the item loop that computes `total`, **before** `db.commit()`.

```python
# src/api/routes/orders.py — inside create_order, after total is computed

from api.models import DiscountCode  # add to existing import

discount_code_str: str | None = None
discounted_total: int | None = None

if payload.discount_code is not None:
    dc = db.query(DiscountCode).filter(DiscountCode.code == payload.discount_code).one_or_none()
    if dc is None:
        raise HTTPException(status_code=422, detail=f"unknown discount code '{payload.discount_code}'")
    discount_code_str = dc.code
    discounted_total = round(total * (1 - dc.percentage / 100))

order.total = total
order.discount_code = discount_code_str
order.discounted_total = discounted_total
db.commit()
```

**Rounding (PRD Open Question #2):** Use `round()` — Python's built-in banker's rounding, consistent with the existing `_to_cents()` which also uses `int(round(...))`. No new rounding convention introduced.

**`discounted_total` is never negative:** `round(total × (1 − 0.20))` on any non-negative integer `total` yields ≥ 0. The allowed percentages (5, 10, 20) guarantee this without an explicit `max(0, ...)` guard, but one can be added defensively if desired.

### 5.2 `OrderOut` construction — update both call sites

Both `create_order` and `get_order` build `OrderOut(...)` manually (no `from_attributes`). Both must be updated to pass the two new fields:

```python
return OrderOut(
    id=order.id,
    user_id=order.user_id,
    total=order.total,
    created_at=order.created_at.strftime("%Y-%d-%m"),
    items=[OrderItemOut(sku=i.sku, quantity=i.quantity, unit_price=i.unit_price) for i in order.items],
    discount_code=order.discount_code,
    discounted_total=order.discounted_total,
)
```

`order.discount_code` and `order.discounted_total` are `None` for orders without a code, which correctly populates the nullable response fields.

---

## 6. Test Strategy

### 6.1 `db` fixture — minimal conftest addition

Tests need to seed `DiscountCode` rows before calling the HTTP client. The existing `db_engine` fixture creates the schema; a `db` fixture wraps it in a session:

```python
# tests/conftest.py — add alongside existing fixtures

@pytest.fixture
def db(db_engine):
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()
```

Both `client` and `db` depend on `db_engine`. Because `db_engine` is function-scoped (default), both fixtures operate against the same in-memory database within a single test.

### 6.2 New test file: `tests/test_discount.py`

Helper pattern mirrors existing `_make_user()` in `test_orders.py`:

```python
def _make_user(client, email="u@example.com", name="U"):
    r = client.post("/users", json={"email": email, "name": name})
    assert r.status_code == 201
    return r.json()

def _seed_code(db, code: str, percentage: int):
    from api.models import DiscountCode
    dc = DiscountCode(code=code, percentage=percentage)
    db.add(dc)
    db.commit()
```

**Required tests (maps to PRD FR-1 / FR-2 / FR-3 consequences):**

| Test | Verifies |
|---|---|
| `test_discount_5_percent` | 5% code → `discounted_total = round(total * 0.95)` |
| `test_discount_10_percent` | 10% code → `discounted_total = round(total * 0.90)` |
| `test_discount_20_percent` | 20% code → `discounted_total = round(total * 0.80)` |
| `test_unknown_discount_code_returns_422` | Unknown code → HTTP 422, descriptive detail |
| `test_no_discount_code_regression` | No `discount_code` field → HTTP 201, `total` unchanged |
| `test_no_discount_fields_are_null` | No code → `discount_code: null`, `discounted_total: null` in response |
| `test_discount_visible_on_get_order` | GET after POST returns same `discount_code` + `discounted_total` |

---

## 7. Key Decisions Summary

| # | Decision | Rationale |
|---|---|---|
| 1 | Percentage validated in app layer only (no `CheckConstraint`) | SQLite `CHECK` not reliably enforced; Pydantic/route validation is the consistent pattern |
| 2 | Discount lookup inline in route (not a helper function) | ~6 lines; YAGNI — one call site, rule-of-three not met |
| 3 | `round()` for discounted total | Consistent with existing `_to_cents()` rounding convention |
| 4 | Null fields always present in response (not omitted) | Avoids `KeyError` in typed clients; consistent with nullable field convention |
| 5 | `DiscountCode` has no back-reference to `Order` | No query joins needed; avoids unnecessary relationship overhead |
| 6 | Seed codes via `db` fixture in tests | Cleanest approach without an admin API; mirrors SQLAlchemy session pattern already present in conftest |
| 7 | Both `create_order` and `get_order` updated | `get_order` must return the stored fields; both use manual `OrderOut(...)` construction |

---

## 8. What Does NOT Change

- `main.py` — no new router to include
- `deps.py` — no new dependency
- `users.py` — unrelated
- `utils/` — `format_order_date` is unchanged
- `conftest.py` — one new fixture only; existing fixtures untouched
- `test_orders.py`, `test_users.py`, `test_dates.py` — zero changes required
