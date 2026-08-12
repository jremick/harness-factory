import unittest

from src.inventory import StockItem, reorder_candidates


class ReorderCandidatesTests(unittest.TestCase):
    def test_filters_and_sorts_by_quantity_then_sku(self):
        items = [
            StockItem("  Z-9 ", 5),
            StockItem("a-2", 1),
            StockItem("A-1", 1),
            StockItem("skip", 6),
        ]

        self.assertEqual(reorder_candidates(items, 5), ["A-1", "a-2", "Z-9"])

    def test_rejects_negative_threshold(self):
        with self.assertRaises(ValueError):
            reorder_candidates([], -1)


if __name__ == "__main__":
    unittest.main()

