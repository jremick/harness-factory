import ast
import copy
import sys
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(sys.argv.pop(1)).resolve()
MODE = sys.argv.pop(1) if len(sys.argv) > 1 else "harness"
sys.path.insert(0, str(ROOT))
from src.invoice import calculate_total  # noqa: E402


class Acceptance(unittest.TestCase):
    def test_behavior_and_no_mutation(self) -> None:
        lines = [{"quantity": 3, "unit_price": Decimal("0.10")}, {"quantity": 1, "unit_price": Decimal("2.005")}]
        original = copy.deepcopy(lines)
        self.assertEqual(calculate_total(lines), Decimal("2.305"))
        self.assertEqual(lines, original)
        for invalid in (None, (), [{}], [{"quantity": 0, "unit_price": Decimal("1")}], [{"quantity": 1, "unit_price": 1}]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                calculate_total(invalid)

    def test_private_helper_was_extracted(self) -> None:
        tree = ast.parse((ROOT / "src/invoice.py").read_text())
        names = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
        self.assertIn("calculate_total", names)
        self.assertTrue(any(name.startswith("_") for name in names), names)
        self.assertEqual([name for name in names if not name.startswith("_")], ["calculate_total"])

    def test_harness_evidence(self) -> None:
        if MODE == "baseline":
            self.skipTest("baseline has no harness evidence contract")
        import json
        records = [json.loads(line) for line in (ROOT / "evidence/ledger.jsonl").read_text().splitlines() if line]
        self.assertTrue(any(item.get("exitCode") == 0 and "REQ-PROCESS-VERIFY" in item.get("requirementIds", []) for item in records))
        self.assertEqual(json.loads((ROOT / "evidence/run-summary.json").read_text()).get("status"), "complete")


if __name__ == "__main__":
    unittest.main(verbosity=2)
