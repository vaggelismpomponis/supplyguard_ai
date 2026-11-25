"""
file: tool_lib.py
Pure, read-only tools used throughout the workshop.
"""
from langchain_core.tools import tool


@tool
def get_unit_price(product: str) -> float:
    """Return the unit price in EUR for laptop, monitor, or keyboard."""
    prices = {"laptop": 900.0, "monitor": 250.0, "keyboard": 40.0}
    key = product.strip().lower()
    if key not in prices:
        raise ValueError(f"Unknown product: {product}")
    return prices[key]


@tool
def calculate_total(unit_price: float, quantity: int) -> float:
    """Calculate an order total in EUR, excluding tax and shipping."""
    if unit_price < 0 or quantity < 1:
        raise ValueError("Price must be nonnegative and quantity at least 1.")
    return round(unit_price * quantity, 2)


TOOLS = [get_unit_price, calculate_total]
