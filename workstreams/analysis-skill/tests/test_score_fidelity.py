import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "score_fidelity.py"
SPEC = importlib.util.spec_from_file_location("score_fidelity", MODULE_PATH)
assert SPEC and SPEC.loader
score_fidelity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(score_fidelity)


def record(path, value, status="declared", confidence=0.9, confirmation=False):
    return {
        "field": path,
        "value": value,
        "claimClass": (
            "absent-or-unknowable" if status == "unknown" else "operational-behavior"
        ),
        "epistemicStatus": status,
        "confidence": confidence,
        "sources": [] if status == "unknown" else [
            {"path": "source.txt", "location": "line 1"}
        ],
        "contradictions": [],
        "missingEvidence": ["Authoritative declaration"] if status in {"unknown", "inferred"} else [],
        "humanConfirmation": {
            "required": confirmation,
            "reason": "Confirm the unresolved value." if confirmation else "",
        },
    }


class FidelityScorerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rubric = json.loads(
            (MODULE_PATH.parent / "fidelity-rubric.json").read_text(encoding="utf-8")
        )

    def test_normalized_text_match(self):
        path = "/purpose/summary"
        actual = {"purpose": {"summary": "  Evidence-backed\n diagnosis  "}}
        evidence = record(path, actual["purpose"]["summary"])
        fact = {
            "id": "PURPOSE",
            "group": "purpose",
            "path": path,
            "expected": "Evidence-backed diagnosis",
            "normalizer": "text",
            "expectedEpistemic": ["declared"],
            "sourcePathsAny": ["source.txt"],
            "humanConfirmation": "not-required",
        }
        result = score_fidelity.classify_fact(fact, actual, evidence, self.rubric)
        self.assertEqual(result["category"], "normalized_match")
        self.assertEqual(result["confidenceCalibrationScore"], 1.0)

    def test_correct_unknown_requires_explicit_record(self):
        path = "/purpose/intendedOutcomes/1/statement"
        actual = {"purpose": {"intendedOutcomes": [{"statement": "Operational outcome"}]}}
        evidence = record(path, None, status="unknown", confidence=0.0)
        fact = {
            "id": "NO-BUSINESS-OUTCOME",
            "group": "purpose",
            "path": path,
            "expectedUnknown": True,
            "expectedEpistemic": ["unknown"],
            "expectedClaimClasses": ["absent-or-unknowable"],
            "humanConfirmation": "not-required",
        }
        result = score_fidelity.classify_fact(fact, actual, evidence, self.rubric)
        self.assertEqual(result["category"], "correct_unknown")
        self.assertIn("hdp-ledger-value-consistency", result["evidenceChecksPassed"])

    def test_invented_value_is_false_assertion(self):
        path = "/purpose/intendedOutcomes/1/statement"
        actual = {
            "purpose": {
                "intendedOutcomes": [
                    {"statement": "Operational outcome"},
                    {"statement": "Increase customer satisfaction by 20 percent"},
                ]
            }
        }
        evidence = record(path, actual["purpose"]["intendedOutcomes"][1]["statement"])
        fact = {
            "id": "NO-BUSINESS-OUTCOME",
            "group": "purpose",
            "path": path,
            "expectedUnknown": True,
            "expectedEpistemic": ["unknown"],
            "expectedClaimClasses": ["absent-or-unknowable"],
            "humanConfirmation": "not-required",
        }
        result = score_fidelity.classify_fact(fact, actual, evidence, self.rubric)
        self.assertEqual(result["category"], "false_assertion")

    def test_skill_assessment_shape_is_normalized(self):
        assessment = {
            "path": "/metadata/name",
            "value": "incident-scribe",
            "epistemicStatus": "declared",
            "confidence": 1.0,
            "evidence": [
                {"source": ".hdp/source-definition.public.json", "location": "/metadata/name"}
            ],
            "contradictions": [],
            "missingEvidence": [],
            "humanConfirmationRequired": False,
        }
        records = score_fidelity.extract_evidence_records(
            {"fieldAssessments": [assessment]}, {}
        )
        self.assertEqual(records[0]["field"], "/metadata/name")
        self.assertEqual(
            records[0]["sources"][0]["path"], ".hdp/source-definition.public.json"
        )
        self.assertFalse(records[0]["humanConfirmation"]["required"])

    def test_remove_pointer_supports_extension_exclusion(self):
        value = {"extensions": {"x-hdp-reconstruction": {"extra": True}, "x-other": 1}}
        score_fidelity.remove_pointer(value, "/extensions/x-hdp-reconstruction")
        self.assertEqual(value, {"extensions": {"x-other": 1}})

    def test_acceptable_difference_must_be_inferred_and_confirmed(self):
        path = "/failures/recoveryPolicies/0/maxAttempts"
        actual = {"failures": {"recoveryPolicies": [{"maxAttempts": 3}]}}
        evidence = record(path, 3, status="inferred", confidence=0.5, confirmation=True)
        fact = {
            "id": "ATTEMPTS",
            "group": "failures",
            "path": path,
            "expected": 2,
            "acceptableAlternatives": [3],
            "normalizer": "exact",
            "expectedEpistemic": ["inferred"],
            "sourcePathsAny": ["source.txt"],
            "humanConfirmation": "required",
        }
        result = score_fidelity.classify_fact(fact, actual, evidence, self.rubric)
        self.assertEqual(result["category"], "acceptable_inferred_difference")

    def test_forbidden_business_outcome_check_is_deterministic(self):
        fact = {
            "id": "NO-BUSINESS-CLAIM",
            "group": "purpose",
            "path": "/purpose/intendedOutcomes",
            "assertion": "no-forbidden-pattern",
            "forbiddenPatterns": ["revenue", r"\b[0-9]+%"],
            "recordOptional": True,
        }
        safe = {"purpose": {"intendedOutcomes": [{"statement": "Draft an incident diagnosis."}]}}
        unsafe = {"purpose": {"intendedOutcomes": [{"statement": "Increase revenue by 20%."}]}}
        safe_result = score_fidelity.classify_fact(fact, safe, None, self.rubric)
        unsafe_result = score_fidelity.classify_fact(fact, unsafe, None, self.rubric)
        self.assertEqual(safe_result["category"], "correct_unknown")
        self.assertEqual(unsafe_result["category"], "false_assertion")
        self.assertEqual(unsafe_result["forbiddenPatternHits"][0]["pattern"], "revenue")

    def test_cli_writes_passing_deterministic_report(self):
        rubric = dict(self.rubric)
        rubric["coverageGroups"] = [
            {"id": "metadata", "prefixes": ["/metadata"], "weight": 1, "critical": False, "minimumFacts": 1}
        ]
        rubric["gates"] = dict(rubric["gates"])
        rubric["gates"].update(
            {
                "minimumOverallScore": 0.9,
                "minimumContentScore": 0.9,
                "minimumEvidenceContractScore": 0.9,
                "minimumConfidenceCalibrationScore": 0.8,
                "minimumCoverage": 1.0,
            }
        )
        actual = {"metadata": {"name": "incident-scribe"}}
        evidence = {"records": [record("/metadata/name", "incident-scribe")]}
        expected = {
            "fixtureId": "self-test",
            "expectStructuralValidity": True,
            "wholeDocumentExpectation": "exact",
            "facts": [
                {
                    "id": "NAME",
                    "group": "metadata",
                    "path": "/metadata/name",
                    "expected": "incident-scribe",
                    "expectedEpistemic": ["declared"],
                    "sourcePathsAny": ["source.txt"],
                    "humanConfirmation": "not-required",
                }
            ],
        }
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["metadata"],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            documents = {
                "rubric.json": rubric,
                "actual.json": actual,
                "evidence.json": evidence,
                "expected.json": expected,
                "schema.json": schema,
                "expected-hdp.json": actual,
            }
            for name, value in documents.items():
                (root / name).write_text(json.dumps(value), encoding="utf-8")
            output = root / "result.json"
            exit_code = score_fidelity.main(
                [
                    "--expected", str(root / "expected.json"),
                    "--actual-hdp", str(root / "actual.json"),
                    "--actual-ledger", str(root / "evidence.json"),
                    "--rubric", str(root / "rubric.json"),
                    "--schema", str(root / "schema.json"),
                    "--expected-hdp", str(root / "expected-hdp.json"),
                    "--output", str(output),
                ]
            )
            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["counts"]["exact_match"], 1)
        self.assertTrue(report["documentComparison"]["exact"])


if __name__ == "__main__":
    unittest.main()
