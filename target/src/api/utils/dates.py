from datetime import datetime


def format_order_date(dt: datetime) -> str:
    return dt.strftime("%Y-%d-%m")
