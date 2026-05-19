from datetime import datetime

from api.utils.dates import format_order_date


def test_format_order_date_basic():
    dt = datetime(2025, 3, 7, 12, 0, 0)
    assert format_order_date(dt) == "2025-07-03"


def test_format_order_date_end_of_year():
    dt = datetime(2024, 12, 31, 23, 59, 59)
    assert format_order_date(dt) == "2024-31-12"
