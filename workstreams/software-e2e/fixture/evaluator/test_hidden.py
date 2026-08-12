from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path


TARGET = Path(os.environ["HDP_EVAL_TARGET"])
sys.path.insert(0, str(TARGET))

from src.inventory import StockItem, reorder_candidates  # noqa: E402


class HiddenReorderCandidateTests(unittest.TestCase):
    def test_accepts_generator_and_keeps_input_unchanged(self):
        source = [StockItem(" b ", 2), StockItem("A", 2), StockItem("later", 7)]
        before = list(source)

        result = reorder_candidates((item for item in source), 2)

        self.assertEqual(result, ["A", "b"])
        self.assertEqual(source, before)

    def test_boundary_is_inclusive(self):
        self.assertEqual(reorder_candidates([StockItem("edge", 0)], 0), ["edge"])

    def test_rejects_boolean_and_non_integer_thresholds(self):
        for invalid in (True, False, 1.5, "2", None):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    reorder_candidates([], invalid)

    def test_rejects_invalid_items(self):
        invalid_items = [
            StockItem("   ", 1),
            StockItem("x", -1),
            StockItem("x", True),
            StockItem("x", 1.5),
        ]
        for invalid in invalid_items:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    reorder_candidates([invalid], 5)

    def test_case_insensitive_order_uses_original_tie_breaker(self):
        items = [StockItem("a", 1), StockItem("A", 1)]
        self.assertEqual(reorder_candidates(items, 1), ["A", "a"])


if __name__ == "__main__":
    unittest.main()

