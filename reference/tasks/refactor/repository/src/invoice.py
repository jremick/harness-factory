"""Invoice arithmetic with deliberately tangled validation."""

from decimal import Decimal


def calculate_total(lines: list[dict[str, object]]) -> Decimal:
    if not isinstance(lines, list):
        raise ValueError("lines must be a list")
    total = Decimal("0")
    for line in lines:
        if not isinstance(line, dict):
            raise ValueError("line must be a mapping")
        quantity = line.get("quantity")
        unit_price = line.get("unit_price")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("quantity must be a positive integer")
        if not isinstance(unit_price, Decimal) or unit_price < 0:
            raise ValueError("unit_price must be a non-negative Decimal")
        total += unit_price * quantity
    return total
