import unittest

from src.statistics import summarize


class StatisticsTests(unittest.TestCase):
    def test_values(self) -> None:
        self.assertEqual(
            summarize([3, -1, 3]),
            {"count": 3, "total": 5, "minimum": -1, "maximum": 3},
        )

    def test_empty(self) -> None:
        self.assertEqual(
            summarize([]),
            {"count": 0, "total": 0, "minimum": None, "maximum": None},
        )

    def test_invalid_input_raises_value_error(self) -> None:
        for value in (None, (), [1, True], [1, 2.5], "1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                summarize(value)


if __name__ == "__main__":
    unittest.main()
