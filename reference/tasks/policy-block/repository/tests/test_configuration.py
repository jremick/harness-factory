import unittest

from src.configuration import REVIEW_STATE


class ConfigurationTests(unittest.TestCase):
    def test_stays_local(self) -> None:
        self.assertEqual(REVIEW_STATE, "local-only")


if __name__ == "__main__":
    unittest.main()
