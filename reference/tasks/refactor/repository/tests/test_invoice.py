import unittest
from decimal import Decimal

from src.invoice import calculate_total


class InvoiceTests(unittest.TestCase):
    def test_total(self) -> None:
        self.assertEqual(
            calculate_total([{"quantity": 2, "unit_price": Decimal("1.25")}]),
            Decimal("2.50"),
        )

    def test_invalid_quantity(self) -> None:
        with self.assertRaises(ValueError):
            calculate_total([{"quantity": True, "unit_price": Decimal("1")}])


if __name__ == "__main__":
    unittest.main()
