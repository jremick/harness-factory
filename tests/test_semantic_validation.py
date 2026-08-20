import copy
import unittest
from pathlib import Path

from hdp.io import load_document
from hdp.semantic_validation import semantic_diagnostics


EXAMPLE = Path(__file__).parents[1] / "examples" / "software-development" / "hdp.yaml"


class SemanticValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.definition = load_document(EXAMPLE)

    def test_allowed_tool_ids_must_resolve(self) -> None:
        definition = copy.deepcopy(self.definition)
        definition["governance"]["permissions"]["tools"]["allowedIds"].append(
            "TOOL-DOES-NOT-EXIST"
        )
        diagnostics = semantic_diagnostics(definition, EXAMPLE.parent)
        self.assertTrue(
            any(
                item.rule_id == "SEM-029"
                and item.instance_path.endswith("/2")
                for item in diagnostics
            ),
            diagnostics,
        )

    def test_unreachable_stage_is_rejected(self) -> None:
        definition = copy.deepcopy(self.definition)
        definition["orchestration"]["stages"].append({
            "id": "STAGE-ORPHAN", "name": "Orphan", "roleIds": ["ROLE-VERIFIER"],
            "entryCriteria": [], "exitCriteria": ["Never reached."], "next": [],
        })
        diagnostics = semantic_diagnostics(definition, EXAMPLE.parent)
        self.assertTrue(any(item.rule_id == "SEM-053" for item in diagnostics), diagnostics)

    def test_stage_cycle_is_rejected(self) -> None:
        definition = copy.deepcopy(self.definition)
        definition["orchestration"]["stages"][-1]["next"] = ["STAGE-ORIENT"]
        diagnostics = semantic_diagnostics(definition, EXAMPLE.parent)
        self.assertTrue(any(item.rule_id == "SEM-054" for item in diagnostics), diagnostics)

    def test_trace_nodes_must_reference_entities_of_the_declared_kind(self) -> None:
        definition = copy.deepcopy(self.definition)
        definition["traceability"]["nodes"][0]["ref"] = "REQ-FUNCTIONAL-RENDER"
        diagnostics = semantic_diagnostics(definition, EXAMPLE.parent)
        self.assertTrue(
            any(item.code == "HDP-SEM-TRACE-REF-MISSING" for item in diagnostics),
            diagnostics,
        )

    def test_output_contract_can_be_a_trace_component(self) -> None:
        definition = copy.deepcopy(self.definition)
        component = next(
            item
            for item in definition["traceability"]["nodes"]
            if item["kind"] == "component"
        )
        component["ref"] = "ARTIFACT-SOFTWARE-DIFF"

        diagnostics = semantic_diagnostics(definition, EXAMPLE.parent)

        self.assertFalse(
            any(item.code == "HDP-SEM-TRACE-REF-MISSING" for item in diagnostics),
            diagnostics,
        )

    def test_trace_edges_must_use_valid_typed_endpoints(self) -> None:
        definition = copy.deepcopy(self.definition)
        definition["traceability"]["edges"][0]["relation"] = "supports"
        diagnostics = semantic_diagnostics(definition, EXAMPLE.parent)
        self.assertTrue(
            any(item.code == "HDP-SEM-TRACE-EDGE-TYPE" for item in diagnostics),
            diagnostics,
        )

    def test_every_actual_outcome_requires_an_ordered_trace_path(self) -> None:
        definition = copy.deepcopy(self.definition)
        definition["traceability"]["nodes"] = [
            item
            for item in definition["traceability"]["nodes"]
            if item["ref"] != "OUTCOME-CORRECT-CHANGE"
        ]
        diagnostics = semantic_diagnostics(definition, EXAMPLE.parent)
        self.assertTrue(
            any(
                item.rule_id == "SEM-063"
                and item.instance_path == "/purpose/intendedOutcomes/0/id"
                for item in diagnostics
            ),
            diagnostics,
        )

    def test_every_must_requirement_requires_its_declared_test_and_evidence_path(self) -> None:
        definition = copy.deepcopy(self.definition)
        process_test = next(
            item
            for item in definition["evaluation"]["tests"]
            if item["id"] == "TEST-EXTERNAL-PROCESS"
        )
        process_test["evidenceArtifactId"] = "ARTIFACT-EVIDENCE"
        diagnostics = semantic_diagnostics(definition, EXAMPLE.parent)
        self.assertTrue(
            any(
                item.rule_id == "SEM-064"
                and "REQ-PROCESS-VERIFY" in item.message
                for item in diagnostics
            ),
            diagnostics,
        )

    def test_controlled_and_higher_profiles_inherit_controlled_obligations(self) -> None:
        for conformance in ("controlled", "production", "high-assurance"):
            with self.subTest(conformance=conformance):
                definition = copy.deepcopy(self.definition)
                definition["runtime"]["profile"]["conformance"] = conformance
                definition["evaluation"]["adversarialTests"] = []
                diagnostics = semantic_diagnostics(definition, EXAMPLE.parent)
                self.assertTrue(
                    any(
                        item.rule_id == "SEM-070"
                        and item.instance_path == "/evaluation/adversarialTests"
                        for item in diagnostics
                    ),
                    diagnostics,
                )

    def test_controlled_profile_requires_external_evaluator(self) -> None:
        definition = copy.deepcopy(self.definition)
        definition["evaluation"]["evaluators"][0]["independence"] = (
            "independent-operator"
        )
        diagnostics = semantic_diagnostics(definition, EXAMPLE.parent)
        self.assertTrue(any(item.rule_id == "SEM-071" for item in diagnostics), diagnostics)

    def test_controlled_profile_requires_deny_default_and_drift_monitoring(self) -> None:
        definition = copy.deepcopy(self.definition)
        definition["governance"]["permissions"]["default"] = "allow"
        definition["monitoring"]["driftRules"] = []
        diagnostics = semantic_diagnostics(definition, EXAMPLE.parent)
        self.assertTrue(any(item.rule_id == "SEM-072" for item in diagnostics), diagnostics)
        self.assertTrue(any(item.rule_id == "SEM-073" for item in diagnostics), diagnostics)

    def test_unknown_required_extension_is_rejected_but_optional_is_preserved(self) -> None:
        envelope = {
            "owner": "https://example.com/hdp",
            "schemaUri": "https://example.com/hdp/feature.schema.json",
            "schemaDigest": "sha256:" + ("a" * 64),
            "version": "1.0.0",
            "required": False,
            "payload": {"feature": "preserve-me"},
        }
        definition = copy.deepcopy(self.definition)
        definition["extensions"]["x-example.feature"] = envelope
        diagnostics = semantic_diagnostics(definition, EXAMPLE.parent)
        self.assertFalse(
            any(item.rule_id == "SEM-080" for item in diagnostics), diagnostics
        )
        self.assertEqual(
            definition["extensions"]["x-example.feature"]["payload"],
            {"feature": "preserve-me"},
        )

        definition["extensions"]["x-example.feature"]["required"] = True
        diagnostics = semantic_diagnostics(definition, EXAMPLE.parent)
        self.assertTrue(any(item.rule_id == "SEM-080" for item in diagnostics), diagnostics)


if __name__ == "__main__":
    unittest.main()
