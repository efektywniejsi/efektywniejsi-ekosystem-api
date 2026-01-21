"""
Utility functions for generating order numbers.
"""

import secrets
from datetime import datetime


def generate_order_number() -> str:
    """
    Generate a unique order number in format: ORD-YYYYMMDD-XXXX

    Example: ORD-20260121-A3F9
    """
    date_part = datetime.now().strftime("%Y%m%d")
    random_part = secrets.token_hex(2).upper()  # 4 character hex string
    return f"ORD-{date_part}-{random_part}"
