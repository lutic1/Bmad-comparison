# Data Model: Fix Order Date Format

**Feature**: 001-fix-order-date-format
**Date**: 2026-05-18

## Affected Entity: Order

No schema changes. The `Order` table and SQLAlchemy model are unchanged.

| Field        | DB Type   | Python Type | Notes                         |
|--------------|-----------|-------------|-------------------------------|
| `id`         | INTEGER   | `int`       | Primary key, unchanged        |
| `user_id`    | INTEGER   | `int`       | FK to users, unchanged        |
| `total`      | INTEGER   | `int`       | Cents, unchanged              |
| `created_at` | DATETIME  | `datetime`  | Stored as naive UTC, unchanged |

## API Response Shape: OrderOut

The `OrderOut` Pydantic model is unchanged in structure. The `created_at`
field remains a `str`; only the value produced by serialization changes.

| Field        | Type              | Before (buggy)  | After (correct) |
|--------------|-------------------|-----------------|-----------------|
| `id`         | `int`             | unchanged        | unchanged        |
| `user_id`    | `int`             | unchanged        | unchanged        |
| `total`      | `int`             | unchanged        | unchanged        |
| `created_at` | `str`             | `"YYYY-DD-MM"`  | `"YYYY-MM-DD"`  |
| `items`      | `list[OrderItemOut]` | unchanged    | unchanged        |

## Invariant

For any `Order` with `created_at = datetime(Y, M, D, ...)`, the serialized
`created_at` string MUST equal `f"{Y:04d}-{M:02d}-{D:02d}"`.
