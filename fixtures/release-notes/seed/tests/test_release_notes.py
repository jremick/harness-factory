import unittest

from src.release_notes import build_release_notes


class PublicReleaseNotesTests(unittest.TestCase):
    def test_empty_release(self) -> None:
        self.assertEqual(
            build_release_notes([]),
            "# Release notes\n\nNo user-visible changes.\n",
        )

    def test_grouping_and_numbered_bullet(self) -> None:
        changes = [
            {"type": "fixed", "summary": "Repair export", "issue": 14},
            {"type": "added", "summary": "Add audit view", "issue": 9},
        ]
        self.assertEqual(
            build_release_notes(changes),
            "# Release notes\n\n## Added\n\n- Add audit view (#9)\n\n"
            "## Fixed\n\n- Repair export (#14)\n",
        )


if __name__ == "__main__":
    unittest.main()

