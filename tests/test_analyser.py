import tempfile
import unittest
from pathlib import Path

from hdp.analyser import analyse_harness
from hdp.compiler import compile_hdp
from hdp.diagnostics import HdpGenerationError, HdpInputError
from hdp.generator import generate_harness
from hdp.io import load_document
from hdp.schema_validation import structural_diagnostics


ROOT = Path(__file__).resolve().parents[1]
FULL_EXAMPLE = ROOT / "examples" / "software-development" / "hdp.yaml"
BINDING = ROOT / "examples" / "software-development" / "bindings" / "codex.yaml"


class AnalyserTests(unittest.TestCase):
    def test_generated_public_source_reconstructs_with_explicit_unknowns(self) -> None:
        with tempfile.TemporaryDirectory() as harness_dir, tempfile.TemporaryDirectory() as output_dir:
            generate_harness(FULL_EXAMPLE, Path(harness_dir))
            result = analyse_harness(Path(harness_dir), Path(output_dir))
            reconstructed = load_document(Path(output_dir) / "hdp.reconstructed.yaml")
            extension = reconstructed["extensions"]["x-hdp-reconstruction"]
            self.assertFalse(result["valid"])
            self.assertFalse(extension["generationReady"])
            self.assertEqual(
                extension["sourceMode"], "embedded-generated-public-projection"
            )
            self.assertGreater(result["fieldAssessmentCount"], 500)
            self.assertNotEqual(structural_diagnostics(reconstructed), [])
            self.assertEqual(result["semanticStatus"], "not-run")
            evidence_map = load_document(Path(output_dir) / "evidence-map.json")
            records = {item["field"]: item for item in evidence_map["records"]}
            self.assertEqual(
                records["/evaluation/tests/0/expected"]["epistemicStatus"],
                "unknown",
            )
            self.assertEqual(
                records["/evaluation/tests/0/expected"]["claimClass"],
                "absent-or-unknowable",
            )
            self.assertFalse(
                any(
                    field.startswith("/extensions/x-hdp-reconstruction/")
                    for field in records
                )
            )

    def test_arbitrary_harness_requires_skill_reasoning(self) -> None:
        with tempfile.TemporaryDirectory() as harness_dir, tempfile.TemporaryDirectory() as output_dir:
            Path(harness_dir, "AGENTS.md").write_text("Run tests.\n")
            with self.assertRaises(HdpInputError):
                analyse_harness(Path(harness_dir), Path(output_dir))

    def test_reconstructed_public_source_blocks_recompilation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "original"
            analysis = root / "analysis"
            compile_hdp(FULL_EXAMPLE, BINDING, original)
            analyse_harness(original, analysis)
            reconstructed = analysis / "hdp.reconstructed.yaml"
            extracted_binding = analysis / "codex-binding.yaml"

            binding = load_document(extracted_binding)
            self.assertEqual(
                binding["externallyEnforcedResources"],
                ["environment", "filesystem", "network", "process", "wall-time"],
            )
            with self.assertRaises(HdpGenerationError):
                compile_hdp(reconstructed, extracted_binding, root / "recompiled")

    def test_analyser_rejects_input_and_output_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            harness = root / "harness"
            harness.mkdir()
            outside = root / "outside.txt"
            outside.write_text("private\n")
            (harness / "escape.txt").symlink_to(outside)
            with self.assertRaisesRegex(HdpInputError, "symlink"):
                analyse_harness(harness, root / "analysis", allow_partial=True)

            clean = root / "clean"
            clean.mkdir()
            (clean / "AGENTS.md").write_text("Run tests.\n")
            output_target = root / "output-target"
            output_target.mkdir()
            output_link = root / "output-link"
            output_link.symlink_to(output_target, target_is_directory=True)
            with self.assertRaisesRegex(HdpInputError, "symlink"):
                analyse_harness(clean, output_link, allow_partial=True)

    def test_analyser_rejects_output_inside_inspected_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "AGENTS.md").write_text("Run tests.\n")
            with self.assertRaisesRegex(HdpInputError, "outside"):
                analyse_harness(root, root / "analysis", allow_partial=True)


if __name__ == "__main__":
    unittest.main()
