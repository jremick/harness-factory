import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hdp.diagnostics import HdpGenerationError
from hdp.generator import generate_harness
from hdp.io import load_document


ROOT = Path(__file__).resolve().parents[1]
FULL_EXAMPLE = ROOT / "examples" / "software-development" / "hdp.yaml"


def artifact_hashes(manifest):
    return {item["path"]: item["sha256"] for item in manifest["artifacts"]}


class GeneratorTests(unittest.TestCase):
    def test_generation_is_deterministic_and_has_no_private_canary(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            one = generate_harness(FULL_EXAMPLE, Path(first))
            two = generate_harness(FULL_EXAMPLE, Path(second))
            self.assertEqual(artifact_hashes(one), artifact_hashes(two))
            text = "\n".join(
                path.read_text(encoding="utf-8", errors="ignore")
                for path in Path(first).rglob("*") if path.is_file()
            )
            self.assertNotIn("HDP_PRIVATE_CANARY_8F5C2E71", text)
            self.assertNotIn("urn:artifact:evaluator:release-notes:v1", text)

            public = load_document(Path(first) / ".hdp/source-definition.public.json")
            hidden_fixture = next(
                item for item in public["evaluation"]["fixtures"]
                if item["visibility"] == "hidden"
            )
            self.assertEqual(hidden_fixture["visibility"], "hidden")
            self.assertRegex(hidden_fixture["commitment"], r"^sha256:[0-9a-f]{64}$")
            hidden_test = next(
                item for item in public["evaluation"]["tests"]
                if item["visibility"] == "hidden"
            )
            self.assertIn("expected", hidden_test)
            self.assertTrue(all(
                item["implementationRef"].startswith("urn:artifact:evaluator:")
                for item in public["evaluation"]["evaluators"]
            ))

    def test_manual_extension_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            generate_harness(FULL_EXAMPLE, output)
            manual = output / "manual" / "operator-note.md"
            manual.parent.mkdir()
            manual.write_text("keep me\n")
            generate_harness(FULL_EXAMPLE, output)
            self.assertEqual(manual.read_text(), "keep me\n")

    def test_changed_generated_file_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            generate_harness(FULL_EXAMPLE, output)
            agents = output / "AGENTS.md"
            agents.write_text(agents.read_text() + "manual edit\n")
            with self.assertRaises(HdpGenerationError):
                generate_harness(FULL_EXAMPLE, output)

    def test_nonempty_unmanaged_output_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "existing.txt").write_text("user data")
            with self.assertRaises(HdpGenerationError):
                generate_harness(FULL_EXAMPLE, output)

    def test_regeneration_removes_stale_managed_file_and_matches_fresh_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as fresh:
            output = Path(directory)
            generate_harness(
                FULL_EXAMPLE,
                output,
                additional_files={"legacy.txt": "old\n"},
                additional_source_map={"legacy.txt": ["/metadata"]},
            )
            manual = output / "manual" / "note.txt"
            manual.parent.mkdir()
            manual.write_text("preserve\n")

            regenerated = generate_harness(FULL_EXAMPLE, output)
            clean = generate_harness(FULL_EXAMPLE, Path(fresh))

            self.assertFalse((output / "legacy.txt").exists())
            self.assertEqual(manual.read_text(), "preserve\n")
            self.assertEqual(regenerated, clean)
            self.assertEqual(artifact_hashes(regenerated), artifact_hashes(clean))

    def test_modified_stale_file_requires_force_then_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            generate_harness(
                FULL_EXAMPLE,
                output,
                additional_files={"legacy.txt": "old\n"},
                additional_source_map={"legacy.txt": ["/metadata"]},
            )
            (output / "legacy.txt").write_text("manual change\n")
            with self.assertRaises(HdpGenerationError):
                generate_harness(FULL_EXAMPLE, output)
            generate_harness(FULL_EXAMPLE, output, force_generated=True)
            self.assertFalse((output / "legacy.txt").exists())

    def test_output_symlink_and_nested_symlink_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            output_link = root / "linked-output"
            output_link.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(HdpGenerationError, "symlink"):
                generate_harness(FULL_EXAMPLE, output_link)
            self.assertEqual(list(outside.iterdir()), [])

            output = root / "generated"
            generate_harness(FULL_EXAMPLE, output)
            (output / "manual").mkdir()
            (output / "manual" / "escape").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(HdpGenerationError, "symlink"):
                generate_harness(FULL_EXAMPLE, output)

    def test_additional_path_escape_and_unmanaged_regeneration_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "generated"
            with self.assertRaisesRegex(HdpGenerationError, "unsafe"):
                generate_harness(
                    FULL_EXAMPLE, output, additional_files={"../escape": "bad"}
                )
            self.assertFalse((root / "escape").exists())
            with self.assertRaisesRegex(HdpGenerationError, "manual extension root"):
                generate_harness(
                    FULL_EXAMPLE,
                    output,
                    additional_files={"manual/generated.txt": "bad"},
                )

            generate_harness(FULL_EXAMPLE, output)
            (output / "unmanaged.txt").write_text("not under manual\n")
            with self.assertRaisesRegex(HdpGenerationError, "unmanaged"):
                generate_harness(FULL_EXAMPLE, output)

    def test_direct_generator_marks_missing_external_controls_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            generate_harness(FULL_EXAMPLE, output)
            policy = load_document(output / ".hdp/runtime-policy.json")
            self.assertEqual(
                policy["unsupportedEnforcementResources"],
                ["environment", "filesystem", "network", "process", "wall-time"],
            )
            denied = subprocess.run(
                [
                    sys.executable, "scripts/harnessctl.py", "run", "--",
                    "python3", "-c", "print('must not run')",
                ],
                cwd=output, capture_output=True, text=True, check=False,
            )
            self.assertEqual(denied.returncode, 78)
            self.assertNotIn("must not run", denied.stdout)
            self.assertIn("lack an external enforcement binding", denied.stderr)

    def test_runtime_overlay_cannot_replace_canonical_network_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(HdpGenerationError, "runtime policy overlay"):
                generate_harness(
                    FULL_EXAMPLE,
                    Path(directory),
                    runtime_policy_overlay={"network": {"allowed": True}},
                )


if __name__ == "__main__":
    unittest.main()
