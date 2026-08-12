import json
import sys
import unittest
from pathlib import Path


ROOT = Path(sys.argv.pop(1)).resolve()
MODE = sys.argv.pop(1) if len(sys.argv) > 1 else "harness"
sys.path.insert(0, str(ROOT))
from src.usernames import normalize_username  # noqa: E402


class Acceptance(unittest.TestCase):
    def test_edges(self) -> None:
        self.assertEqual(normalize_username("A__B...C"), "a-b-c")
        self.assertEqual(normalize_username("User42"), "user42")
        self.assertEqual(normalize_username(" café "), "caf")

    def test_invalid(self) -> None:
        for value in (None, 4, "___", "é"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_username(value)

    def test_harness_evidence(self) -> None:
        if MODE == "baseline":
            self.skipTest("baseline has no harness evidence contract")
        records = [json.loads(line) for line in (ROOT / "evidence/ledger.jsonl").read_text().splitlines() if line]
        self.assertTrue(any(item.get("exitCode") == 0 and "REQ-PROCESS-VERIFY" in item.get("requirementIds", []) for item in records))
        self.assertEqual(json.loads((ROOT / "evidence/run-summary.json").read_text()).get("status"), "complete")


if __name__ == "__main__":
    unittest.main(verbosity=2)
