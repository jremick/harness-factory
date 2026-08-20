import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from hdp.io import load_document
from hdp.schema_validation import load_canonical_schema, structural_diagnostics
from hdp.semantic_validation import semantic_diagnostics


ROOT = Path(__file__).resolve().parents[1]
FULL_EXAMPLE = ROOT / "examples" / "software-development" / "hdp.yaml"
CANONICAL_SCHEMA = ROOT / "src" / "hdp" / "schemas" / "hdp.schema.json"
ANALYSIS_SKILL_SCHEMA = (
    ROOT / "skills" / "analyse-existing-harness" / "references" / "hdp.schema.json"
)
HDP_DRAFT_0_1_SCHEMA_SHA256 = (
    "4cb4a85dcdfe6b176be5760a1f109c720a66ea80a6179f94928e3683f1566e96"
)


class SchemaValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.valid = load_document(FULL_EXAMPLE)

    def test_canonical_schema_meta_validates(self) -> None:
        schema = load_canonical_schema()
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_canonical_and_analysis_skill_schema_match_hdp_draft_0_1(self) -> None:
        canonical = CANONICAL_SCHEMA.read_bytes()
        self.assertEqual(
            hashlib.sha256(canonical).hexdigest(), HDP_DRAFT_0_1_SCHEMA_SHA256
        )
        self.assertEqual(ANALYSIS_SKILL_SCHEMA.read_bytes(), canonical)

    def test_full_example_is_structurally_and_semantically_valid(self) -> None:
        self.assertEqual(structural_diagnostics(self.valid), [])
        self.assertEqual(semantic_diagnostics(self.valid, FULL_EXAMPLE.parent), [])

    def test_structural_error_is_stable(self) -> None:
        invalid = copy.deepcopy(self.valid)
        del invalid["metadata"]["version"]
        diagnostics = structural_diagnostics(invalid)
        self.assertTrue(any(item.code == "HDP-STRUCTURE" for item in diagnostics))
        self.assertTrue(any(item.instance_path == "/metadata" for item in diagnostics))

    def test_must_requirement_requires_a_verification(self) -> None:
        invalid = copy.deepcopy(self.valid)
        invalid["requirements"][0]["verificationIds"] = []
        diagnostics = structural_diagnostics(invalid)
        self.assertTrue(
            any(
                item.code == "HDP-STRUCTURE"
                and item.instance_path == "/requirements/0/verificationIds"
                for item in diagnostics
            ),
            diagnostics,
        )

    def test_non_mandatory_requirement_may_defer_verification(self) -> None:
        definition = copy.deepcopy(self.valid)
        definition["requirements"][0]["priority"] = "should"
        definition["requirements"][0]["verificationIds"] = []
        self.assertEqual(structural_diagnostics(definition), [])

    def test_extension_envelope_is_structurally_bounded(self) -> None:
        definition = copy.deepcopy(self.valid)
        definition["extensions"]["x-example.optional"] = {
            "owner": "https://example.com/hdp",
            "schemaUri": "https://example.com/hdp/optional.schema.json",
            "schemaDigest": "sha256:" + ("0" * 64),
            "version": "1.0.0",
            "required": False,
            "payload": {"feature": "preserved"},
        }
        self.assertEqual(structural_diagnostics(definition), [])

        del definition["extensions"]["x-example.optional"]["schemaDigest"]
        diagnostics = structural_diagnostics(definition)
        self.assertTrue(
            any(
                item.instance_path == "/extensions/x-example.optional"
                for item in diagnostics
            ),
            diagnostics,
        )

    def test_unresolved_reference_is_rejected(self) -> None:
        invalid = copy.deepcopy(self.valid)
        invalid["purpose"]["intendedOutcomes"][0]["measureIds"] = ["MEASURE-MISSING"]
        diagnostics = semantic_diagnostics(invalid, FULL_EXAMPLE.parent)
        self.assertTrue(any(item.code == "HDP-SEM-UNRESOLVED-REF" for item in diagnostics))

    def test_network_contradiction_is_rejected(self) -> None:
        invalid = copy.deepcopy(self.valid)
        invalid["governance"]["permissions"]["network"]["destinations"] = ["example.com"]
        diagnostics = semantic_diagnostics(invalid, FULL_EXAMPLE.parent)
        self.assertTrue(any(item.code == "HDP-SEM-NETWORK-CONTRADICTION" for item in diagnostics))

    def test_hidden_fixture_path_is_rejected(self) -> None:
        invalid = copy.deepcopy(self.valid)
        invalid["evaluation"]["fixtures"][1]["publicPath"] = "private/cases.json"
        diagnostics = semantic_diagnostics(invalid, FULL_EXAMPLE.parent)
        self.assertTrue(any(item.code == "HDP-SEM-HIDDEN-FIXTURE-LEAK" for item in diagnostics))

    def test_self_evaluator_is_rejected(self) -> None:
        invalid = copy.deepcopy(self.valid)
        invalid["evaluation"]["evaluators"][0]["independence"] = "self"
        diagnostics = semantic_diagnostics(invalid, FULL_EXAMPLE.parent)
        self.assertTrue(any(item.code == "HDP-SEM-EVALUATOR-NOT-INDEPENDENT" for item in diagnostics))

    def test_unresolved_must_is_rejected(self) -> None:
        invalid = copy.deepcopy(self.valid)
        invalid["requirements"][0]["status"] = "unresolved"
        diagnostics = semantic_diagnostics(invalid, FULL_EXAMPLE.parent)
        self.assertTrue(any(item.code == "HDP-SEM-UNRESOLVED-MUST" for item in diagnostics))

    def test_missing_hard_walltime_is_rejected(self) -> None:
        invalid = copy.deepcopy(self.valid)
        invalid["resources"]["budgets"] = [
            item for item in invalid["resources"]["budgets"] if item["resource"] != "wall-time"
        ]
        diagnostics = semantic_diagnostics(invalid, FULL_EXAMPLE.parent)
        self.assertTrue(any(item.code == "HDP-SEM-NO-HARD-WALLTIME" for item in diagnostics))


if __name__ == "__main__":
    unittest.main()
