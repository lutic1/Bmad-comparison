---
title: Technical Architecture — Percentage Discount Codes at Checkout
prd: _bmad-output/planning-artifacts/prds/prd-target-2026-05-19/prd.md
status: final
created: 2026-05-19
---

# Technical Architecture: Percentage Discount Codes at Checkout

## 1. Overview

Four files change. No new modules, no new dependencies, no migrations script (operator wipes `app.db` between runs). The feature threads a single optional string through `POST /orders`, validates it against a new `discount_codes` table, applies integer-math discounting, and persists the result alongside the order.

---

## 2. Open Question Resolutions

| OQ | Decision | Rationale |
|----|----------|-----------|
| OQ-1 Race conditions | Last-write-wins; no pessimistic lock | SQLite serialises all writes at the file level. Concurrent checkout of the same last redemption of a single-use code is practically impossible in this deployment context. Revisit if the service moves to Postgres. |
| OQ-2 `original_total` storage | Persisted column on `orders` | Consistent with the cents-storage pattern; avoids recomputation; provides an audit trail. Column is `NOT NULL`; non-discounted orders store `original_total == total`. |
| OQ-3 Case sensitivity | Fold to uppercase at lookup (`code.upper()`) | Simplest approach: no DB collation change, no index change. Seeding scripts must insert codes in uppercase by convention. |
| OQ-4 GET ownership gate | No change | Ownership check stays. Discount fields are visible to the owning user only — acceptable. |
| OQ-5 `max_uses = null` | Supported (unlimited) | Required: the PRD names both single-use and multi-use codes as first-class concepts. |

---

## 3. File Change Map

| File | Change type | Summary |
|------|-------------|---------|
| `src/api/models.py` | Extend | Add `DiscountCode` model; add 3 columns to `Order` |
| `src/api/routes/orders.py` | Extend | Extend `OrderCreate`, `OrderOut`; extend `create_order` logic; extend `get_order` response |
| `tests/conftest.py` | Extend | Add `db` session fixture (enables direct DB seeding in tests) |
| `tests/test_discounts.py` | New file | All discount-specific tests (FR-6) |

No other files change.

---

## 4. Data Layer (`src/api/models.py`)

### 4.1 New model: `DiscountCode`

```python
class DiscountCode(Base):
    __tablename__ = "discount_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    percentage: Mapped[int] = mapped_column(Integer, nullable=False)  # 5, 10, or 20
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)   # null = unlimited
    times_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
```

`Boolean` is already available via SQLAlchemy's type system — no new import beyond adding `Boolean` to the existing `sqlalchemy` import.

### 4.2 Extended `Order` model

Three new nullable columns added to the existing `Order` class:

```python
original_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
discount_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
discount_percentage: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

`original_total` is `NOT NULL` with `default=0`; both values are set explicitly in the route before commit, so the default is only a DB-level safety net.

---

## 5. API Layer (`src/api/routes/orders.py`)

### 5.1 Pydantic schema changes

**`OrderCreate`** — add one optional field:

```python
class OrderCreate(BaseModel):
    items: list[OrderItemIn]
    discount_code: str | None = None
```

**`OrderOut`** — add three fields:

```python
class OrderOut(BaseModel):
    id: int
    user_id: int
    total: int
    original_total: int
    discount_code: str | None
    discount_percentage: int | None
    created_at: str
    items: list[OrderItemOut]
```

### 5.2 `create_order` logic changes

The new logic slots in after the existing item-total loop and before `db.commit()`. Inline in the route — 3 validation checks are one call site, no helper warranted yet.

```python
# After existing total-accumulation loop:
original_total = total   # cents, pre-discount

applied_code: str | None = None
applied_pct: int | None = None

if payload.discount_code:
    dc = db.query(DiscountCode).filter(
        DiscountCode.code == payload.discount_code.upper()
    ).one_or_none()
    if dc is None:
        raise HTTPException(status_code=400, detail="discount code not found")
    if not dc.is_active:
        raise HTTPException(status_code=400, detail="discount code is not active")
    if dc.max_uses is not None and dc.times_used >= dc.max_uses:
        raise HTTPException(status_code=400, detail="discount code has been fully redeemed")
    total = original_total * (100 - dc.percentage) // 100
    dc.times_used += 1
    applied_code = dc.code
    applied_pct = dc.percentage

order.total = total
order.original_total = original_total
order.discount_code = applied_code
order.discount_percentage = applied_pct
```

**Discount math:** `original_total * (100 - percentage) // 100`

Integer floor division naturally implements floor-to-nearest-cent. No `math.floor()` needed.

Verification:
- 10% off $100.00 → `10000 * 90 // 100 = 9000` ✓
- 5% off $10.01 → `1001 * 95 // 100 = 95095 // 100 = 950` ✓

**Transaction safety:** `dc.times_used += 1` and `order.*` writes are in the same `db.commit()` call that already exists. If the commit fails, neither persists.

### 5.3 `create_order` response change

Replace the current manual `OrderOut(...)` construction with one that includes the three new fields:

```python
return OrderOut(
    id=order.id,
    user_id=order.user_id,
    total=order.total,
    original_total=order.original_total,
    discount_code=order.discount_code,
    discount_percentage=order.discount_percentage,
    created_at=order.created_at.strftime("%Y-%d-%m"),
    items=[...],
)
```

### 5.4 `get_order` response change

Same extension — add the three new fields to the `OrderOut(...)` constructor in `get_order`. No logic change; reads persisted columns.

### 5.5 New import

Add `DiscountCode` to the import from `api.models` at the top of `orders.py`.

---

## 6. Test Infrastructure (`tests/conftest.py`)

Add a `db` session fixture so discount-code tests can seed records directly:

```python
@pytest.fixture
def db(db_engine):
    from sqlalchemy.orm import sessionmaker as _sm
    Session = _sm(bind=db_engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
```

This derives from the existing `db_engine` fixture, so it shares the same in-memory database as `client` within a test. Tests that need both declare `def test_foo(client, db)`.

---

## 7. Tests (`tests/test_discounts.py`)

New file. All tests use `client` + `db` fixtures. A module-level helper seeds a `DiscountCode`:

```python
from api.models import DiscountCode

def _seed_code(db, code="SAVE10", percentage=10, is_active=True, max_uses=None, times_used=0):
    dc = DiscountCode(
        code=code,
        percentage=percentage,
        is_active=is_active,
        max_uses=max_uses,
        times_used=times_used,
    )
    db.add(dc)
    db.commit()
    return dc
```

### Test matrix (FR-6)

| Test name | Scenario |
|-----------|----------|
| `test_discount_applied_correct_total` | Valid 10% code → total, original_total, discount fields correct |
| `test_discount_times_used_incremented` | After checkout, `times_used` is 1 |
| `test_discount_5pct_rounding` | 5% on 1001 cents → 950 (floor) |
| `test_discount_20pct` | 20% code → correct total |
| `test_no_discount_code_backward_compat` | No code → `discount_code: null`, `original_total == total` |
| `test_unknown_code_returns_400` | Unknown code → 400, "discount code not found" |
| `test_inactive_code_returns_400` | `is_active=False` code → 400, "discount code is not active" |
| `test_exhausted_single_use_code_returns_400` | `max_uses=1, times_used=1` → 400, "has been fully redeemed" |
| `test_case_insensitive_lookup` | Lowercase `"save10"` resolves same as `"SAVE10"` |
| `test_get_order_returns_discount_fields` | `GET /orders/{id}` returns discount fields after discounted checkout |
| `test_get_order_no_discount_fields_null` | `GET /orders/{id}` returns null discount fields for non-discounted order |

---

## 8. What Does Not Change

- `src/api/deps.py` — no change
- `src/api/main.py` — no change (schema created from `Base.metadata` automatically picks up new table/columns)
- `src/api/routes/users.py` — no change
- `src/api/utils/dates.py` — no change
- `tests/test_orders.py` — existing tests continue to pass; `OrderOut` gains nullable fields with null values for non-discounted orders, which does not break assertions that don't check those fields
- `tests/test_users.py`, `tests/test_dates.py` — no change
- `pyproject.toml` — no new dependencies

---

## 9. Constraints Observed

- **No migrations.** New `discount_codes` table and new `Order` columns appear automatically via `Base.metadata.create_all` at startup. Operator wipes `app.db` between runs.
- **No new third-party libraries.** `Boolean` is from SQLAlchemy already present; floor division is stdlib.
- **No auth changes.** Discount code lookup uses the existing `get_db` session; no new dependency injection.
- **Inline logic.** Three-check validation block stays in the route; it's one call site. Extract if a second route ever needs the same checks.
