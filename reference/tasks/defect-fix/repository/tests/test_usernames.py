import unittest

from src.usernames import normalize_username


class UsernameTests(unittest.TestCase):
    def test_normalizes_spacing(self) -> None:
        self.assertEqual(normalize_username("  Ada  Lovelace "), "ada-lovelace")

    def test_rejects_empty(self) -> None:
        with self.assertRaises(ValueError):
            normalize_username("---")


if __name__ == "__main__":
    unittest.main()
