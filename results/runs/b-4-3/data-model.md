# Data Model: Checkout Discount Code

## New Entity: DiscountCode

**Table**: `discount_codes`

| Column           | Type        | Constraints                        | Notes                            |
|------------------|-------------|-------------------------------------|----------------------------------|
| id               | Integer     | PK, autoincrement                  |                                  |
| code             | String(64)  | unique, not null, index            | Stored uppercase                 |
| discount_percent | Integer     | not null, check in {5, 10, 20}     | Percentage: 5, 10, or 20        |
| created_at       | DateTime    | not null, default=utcnow           |                                  |

**Validation rules**:
- `discount_percent` MUST be one of: 5, 10, 20.
- `code` is normalized to uppercase before storage and lookup.
- Uniqueness is enforced at the DB level on the `code` column.

**SQLAlchemy model (declarative `Mapped[...]` style)**:
```python
class DiscountCode(Base):
    __tablename__ = "discount_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    discount_percent: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    orders: Mapped[list["Order"]] = relationship(back_populates="discount_code")
```

**Seed data** (loaded idempotently at startup):
| code     | discount_percent |
|----------|-----------------|
| SAVE5    | 5               |
| SAVE10   | 10              |
| SAVE20   | 20              |

---

## Modified Entity: Order

**Table**: `orders` — two new nullable columns added.

| Column               | Type    | Constraints              | Notes                                   |
|----------------------|---------|--------------------------|------------------------------------------|
| discount_code_id     | Integer | FK(discount_codes.id), nullable | NULL when no discount applied     |
| discount_amount_cents| Integer | not null, default=0      | Cents deducted from total; 0 = no discount |

**State transitions**:

```
[no discount]
    total = original_total
    discount_code_id = NULL
    discount_amount_cents = 0

  -- POST /orders/{id}/discount-code (valid code) -->

[discount applied]
    total = original_total - discount_amount_cents
    discount_code_id = <code.id>
    discount_amount_cents = round(pre-discount-total * percent / 100)

  -- DELETE /orders/{id}/discount-code -->

[no discount]  (total restored)
```

**Replacement (apply code when one already active)**:
1. Restore: `total += current discount_amount_cents`
2. Recalculate on restored total, apply new code.

**SQLAlchemy additions to Order**:
```python
discount_code_id: Mapped[int | None] = mapped_column(
    ForeignKey("discount_codes.id"), nullable=True, default=None
)
discount_amount_cents: Mapped[int] = mapped_column(default=0)
discount_code: Mapped["DiscountCode | None"] = relationship(
    back_populates="orders", foreign_keys=[discount_code_id]
)
```

---

## Relationships

```
DiscountCode (1) ──< Order (many)
  one DiscountCode can be referenced by many orders
  one Order references at most one DiscountCode (nullable)
```

---

## Pydantic Schemas

### Request

```python
class DiscountCodeApply(BaseModel):
    code: str  # e.g., "SAVE10" — normalized to uppercase in route
```

### Response (extended OrderOut)

```python
class OrderOut(BaseModel):
    id: int
    user_id: int
    total: int                    # cents, post-discount
    discount_code: str | None     # code string or null
    discount_amount_cents: int    # 0 when no discount
    created_at: str
    items: list[OrderItemOut]
    model_config = ConfigDict(from_attributes=True)
```

> Note: `discount_code` is the string representation (e.g., `"SAVE10"`) resolved from the relationship, not the FK id.
