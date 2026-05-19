---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-target-2026-05-18/prd.md
workflowType: architecture
project_name: target
user_name: Luisticas
date: 2026-05-18
status: final
---

# Architecture: Percentage Discount Codes at Checkout

**Feature:** FR-1 through FR-5 from PRD `prd-target-2026-05-18/prd.md`  
**Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.x (declarative), Pydantic v2, SQLite, pytest

---

## 1. Guiding Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Case sensitivity | Normalise to `UPPER()` on insert and lookup | Simplest correctness; no SQLite collation magic needed |
| Rounding | `round(total_cents * (1 - pct/100))` | Matches Python's banker's rounding; consistent with `_to_cents` pattern |
| Invalid-code HTTP status | `422` | Consistent with FastAPI's own validation error envelope |
| Seed mechanism | `lifespan` startup + test fixture | Production seeds on boot; tests seed via `db` session fixture (no admin API) |
| Percentage enforcement | Application-layer validation only | No `CheckConstraint` — keeps schema simple; only three known codes are seeded |
| Discount stored on Order | `discount_code: str | None`, `discount_pct: int | None` | Audit trail without joins; mirrors existing `total` design |

---

## 2. Data Model Changes

### 2.1 New model: `DiscountCode` — `src/api/models.py`

```python
class DiscountCode(Base):
    __tablename__ = "discount_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    percentage: Mapped[int] = mapped_column(Integer, nullable=False)
```

`code` is stored and compared in **UPPER CASE**. Uniqueness is enforced at the DB level.

### 2.2 Extend `Order` — `src/api/models.py`

Add two nullable columns to the existing `Order` class:

```python
discount_code: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
discount_pct:  Mapped[int | None] = mapped_column(Integer,     nullable=True, default=None)
```

Both default to `None`; existing rows are unaffected (SQLite schema is rebuilt from `Base.metadata` at startup with no migrations).

---

## 3. API Changes

### 3.1 `OrderCreate` — `src/api/routes/orders.py`

Add one optional field:

```python
class OrderCreate(BaseModel):
    items: list[OrderItemIn]
    discount_code: str | None = None   # new
```

### 3.2 `OrderOut` — `src/api/routes/orders.py`

Add two optional fields (additive; no existing consumer breaks):

```python
class OrderOut(BaseModel):
    id: int
    user_id: int
    total: int
    created_at: str
    items: list[OrderItemOut]
    discount_code: str | None = None   # new
    discount_pct:  int | None = None   # new
```

### 3.3 `create_order` handler — `src/api/routes/orders.py`

Insertion point is **before** the item loop. No changes to item-accumulation logic.

```
1. Receive payload (discount_code optional)
2. If discount_code is not None:
     a. Normalise: code_key = payload.discount_code.strip().upper()
     b. db.query(DiscountCode).filter(DiscountCode.code == code_key).one_or_none()
     c. If None → raise HTTPException(422, detail=f"invalid discount code: {payload.discount_code!r}")
     d. Record discount_pct = dc.percentage, applied_code = dc.code
3. Build Order(user_id, total=0), flush
4. Accumulate item total_cents (unchanged)
5. If discount applied: total_cents = round(total_cents * (1 - discount_pct / 100))
6. order.total = total_cents
   order.discount_code = applied_code   (None if no code)
   order.discount_pct  = discount_pct   (None if no code)
7. commit / refresh / return OrderOut (include new fields)
```

`get_order` also returns `OrderOut`; the two new nullable fields are already on the `Order` ORM object so they fall through automatically — no logic change needed in `get_order`.

**New import required:**

```python
from api.models import DiscountCode, Order, OrderItem, User
```

---

## 4. Seeding

### 4.1 Production seed — `src/api/main.py`

After `Base.metadata.create_all`, insert canonical codes if absent:

```python
from api.models import Base, DiscountCode
from api.deps import engine, SessionLocal

@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    _seed_discount_codes()
    yield

def _seed_discount_codes() -> None:
    canonical = [("SAVE5", 5), ("SAVE10", 10), ("SAVE20", 20)]
    with SessionLocal() as db:
        for code, pct in canonical:
            exists = db.query(DiscountCode).filter(DiscountCode.code == code).one_or_none()
            if exists is None:
                db.add(DiscountCode(code=code, percentage=pct))
        db.commit()
```

Idempotent: safe to call on every restart.

### 4.2 Test seed — `tests/conftest.py`

Add a `db` session fixture and a `discount_codes` fixture. Tests that need codes request `discount_codes`:

```python
from sqlalchemy.orm import Session
from api.models import DiscountCode

@pytest.fixture
def db(db_engine):
    session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def discount_codes(db):
    for code, pct in [("SAVE5", 5), ("SAVE10", 10), ("SAVE20", 20)]:
        db.add(DiscountCode(code=code, percentage=pct))
    db.commit()
```

Tests declare the dependency as: `def test_...(client, discount_codes):`.

---

## 5. Test Coverage Plan

File: `tests/test_orders.py` — append to existing module.

| Test name | Scenario | Key assertion |
|-----------|----------|---------------|
| `test_discount_no_code_regression` | POST /orders without discount_code | `total` unchanged, `discount_code` null, `discount_pct` null |
| `test_discount_5pct` | SAVE5 applied to a 2×$9.99 order | `total == round(1998 * 0.95)` == 1898 |
| `test_discount_10pct` | SAVE10 applied | `total == round(1998 * 0.90)` == 1798 |
| `test_discount_20pct` | SAVE20 applied | `total == round(1998 * 0.80)` == 1598 |
| `test_discount_unknown_code` | Unknown code "BOGUS" | HTTP 422, zero orders created |
| `test_discount_case_insensitive` | "save10" (lowercase) | HTTP 201, discount applied |
| `test_discount_fields_on_get_order` | GET /orders/{id} after discounted POST | response includes `discount_code` and `discount_pct` |

All tests request both `client` and `discount_codes` fixtures (except regression test which only needs `client`).

---

## 6. File Change Summary

| File | Change type | What changes |
|------|-------------|--------------|
| `src/api/models.py` | Extend + Add | New `DiscountCode` class; two nullable columns on `Order` |
| `src/api/routes/orders.py` | Extend | `OrderCreate`, `OrderOut` schemas; `create_order` validation + discount logic; import `DiscountCode` |
| `src/api/main.py` | Extend | `_seed_discount_codes()` helper; call in `lifespan` |
| `tests/conftest.py` | Extend | `db` session fixture; `discount_codes` seed fixture |
| `tests/test_orders.py` | Extend | 7 new test functions |

**No files deleted. No new files. No new dependencies.**

---

## 7. Open Questions Resolved

| PRD OQ | Resolution |
|--------|-----------|
| OQ-1: Case sensitivity | Normalise both sides to UPPER — store seeded codes uppercase, `.strip().upper()` on input |
| OQ-2: Seed mechanism | Startup `lifespan` for production; `discount_codes` fixture for tests |
| OQ-3: Rounding | `round()` (Python 3 banker's rounding) |
| OQ-4: HTTP 422 vs 400 | 422 chosen — consistent with FastAPI validation envelope |
| OQ-5: Schema backward compat | Fields are additive with `None` defaults — safe |
