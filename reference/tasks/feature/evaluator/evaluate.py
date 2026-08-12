import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(sys.argv.pop(1)).resolve()
MODE = sys.argv.pop(1) if len(sys.argv) > 1 else "harness"
sys.path.insert(0, str(ROOT))
from src.statistics import summarize  # noqa: E402


class Acceptance(unittest.TestCase):
    def test_contract_and_no_mutation(self) -> None:
        values = [0, -5, 8, 8]
        original = copy.deepcopy(values)
        self.assertEqual(summarize(values), {"count": 4, "total": 11, "minimum": -5, "maximum": 8})
        self.assertEqual(values, original)

    def test_rejects_invalid_inputs(self) -> None:
        for value in (None, (), [1, True], [1, 2.5], "1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                summarize(value)

    def test_harness_evidence(self) -> None:
        if MODE == "baseline":
            self.skipTest("baseline has no harness evidence contract")
        ledger = ROOT / "evidence/ledger.jsonl"
        summary = ROOT / "evidence/run-summary.json"
        self.assertTrue(ledger.is_file())
        records = [json.loads(line) for line in ledger.read_text().splitlines() if line]
        self.assertTrue(any(item.get("exitCode") == 0 and "REQ-PROCESS-VERIFY" in item.get("requirementIds", []) for item in records))
        self.assertEqual(json.loads(summary.read_text()).get("status"), "complete")


if __name__ == "__main__":
    unittest.main(verbosity=2)
