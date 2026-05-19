from decimal import Decimal, ROUND_HALF_UP
from types import MappingProxyType

# Half-up rounding via Decimal: money invariant, not Python's banker's default.
DISCOUNT_CODES: MappingProxyType[str, int] = MappingProxyType(
    {
        "SAVE5": 5,
        "SAVE10": 10,
        "SAVE20": 20,
    }
)


class InvalidDiscountCode(ValueError):
    """Raised when a non-null code does not match a known entry."""


def normalize_code(raw: str) -> str:
    code = raw.strip().upper()
    if not code:
        raise InvalidDiscountCode("empty discount code")
    return code


def resolve_percent(raw: str) -> tuple[str, int]:
    code = normalize_code(raw)
    if code not in DISCOUNT_CODES:
        raise InvalidDiscountCode(f"unknown code: {code}")
    return code, DISCOUNT_CODES[code]


def apply_discount(subtotal_cents: int, percent: int) -> tuple[int, int]:
    discount = (
        Decimal(subtotal_cents) * Decimal(percent) / Decimal(100)
    ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    discount_cents = int(discount)
    return subtotal_cents - discount_cents, discount_cents
