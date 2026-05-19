import pytest

from api.discounts import (
    DISCOUNT_CODES,
    InvalidDiscountCode,
    apply_discount,
    normalize_code,
    resolve_percent,
)


def test_codes_exposed():
    assert "SAVE5" in DISCOUNT_CODES
    assert "SAVE10" in DISCOUNT_CODES
    assert "SAVE20" in DISCOUNT_CODES
    assert DISCOUNT_CODES["SAVE5"] == 5
    assert DISCOUNT_CODES["SAVE10"] == 10
    assert DISCOUNT_CODES["SAVE20"] == 20


def test_codes_are_read_only():
    with pytest.raises(TypeError):
        DISCOUNT_CODES["SAVE99"] = 99  # type: ignore[index]


def test_normalize_code_trims_and_uppercases():
    assert normalize_code("  save10  ") == "SAVE10"
    assert normalize_code("Save20") == "SAVE20"
    assert normalize_code("SAVE5") == "SAVE5"


def test_normalize_code_empty_raises():
    with pytest.raises(InvalidDiscountCode):
        normalize_code("")


def test_normalize_code_whitespace_only_raises():
    with pytest.raises(InvalidDiscountCode):
        normalize_code("   ")


def test_resolve_percent_canonicalizes():
    assert resolve_percent("save10") == ("SAVE10", 10)
    assert resolve_percent("Save20") == ("SAVE20", 20)
    assert resolve_percent("  SAVE5 ") == ("SAVE5", 5)


def test_resolve_percent_unknown_raises():
    with pytest.raises(InvalidDiscountCode):
        resolve_percent("NOPE")


def test_resolve_percent_empty_raises():
    with pytest.raises(InvalidDiscountCode):
        resolve_percent("")


def test_apply_discount_clean_tier_math():
    assert apply_discount(1000, 10) == (900, 100)
    assert apply_discount(2000, 20) == (1600, 400)
    assert apply_discount(1000, 5) == (950, 50)


def test_apply_discount_half_up_boundary():
    # 999 * 5 / 100 = 49.95 → half-up rounds to 50 (banker's would give 50 too here,
    # but the deliberate case: any .5 boundary must round up, not to-even).
    assert apply_discount(999, 5) == (949, 50)


def test_apply_discount_half_up_explicit_half_cent():
    # 10 * 5 / 100 = 0.5 → half-up = 1 (banker's `round` would give 0).
    assert apply_discount(10, 5) == (9, 1)


def test_apply_discount_returns_non_negative_integers():
    total, discount = apply_discount(0, 20)
    assert total == 0
    assert discount == 0
    assert isinstance(total, int)
    assert isinstance(discount, int)
