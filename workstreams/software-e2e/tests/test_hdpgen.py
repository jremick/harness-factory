from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


WORKSTREAM = Path(__file__).resolve().parents[1]
FIXTURE = WORKSTREAM / "fixture"
sys.path.insert(0, str(WORKSTREAM))

import hdpgen  # noqa: E402


def run(*argv: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)


def generated_hashes(target: Path) -> dict[str, str]:
    manifest = json.loads((target / ".hdp" / "manifest.json").read_text(encoding="utf-8"))
    return {item["path"]: item["sha256"] for item in manifest["managed_files"]}


class GeneratorFunctionalTests(unittest.TestCase):
    def copy_repository(self, parent: Path) -> Path:
        target = parent / "repository"
        shutil.copytree(FIXTURE / "repository", target)
        return target

    def test_generates_usable_harness_and_preserves_manual_extensions(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_repository(Path(temporary))
            manifest = hdpgen.generate(FIXTURE / "harness.yaml", target)

            expected = {
                "AGENTS.md",
                ".agents/skills/stockroom-task-delivery/SKILL.md",
                "scripts/check_path.py",
                "scripts/record_step.py",
                "scripts/run_verification.py",
                "scripts/check_completion.py",
                "evidence/verification-ledger.md",
                ".hdp/manifest.json",
                ".hdp/source-map.json",
                ".hdp/requirements.json",
                ".hdp/roles/implementer.md",
                ".hdp/roles/verifier.md",
                "AGENTS.local.md",
                ".hdp/manual/README.md",
            }
            self.assertTrue(expected.issubset({path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()}))
            self.assertRegex(manifest["trace_id"], r"^HDP-[A-F0-9]{16}$")

            extension = target / "AGENTS.local.md"
            extension.write_text(extension.read_text(encoding="utf-8") + "\nManual marker.\n", encoding="utf-8")
            before = extension.read_bytes()
            second = hdpgen.generate(FIXTURE / "harness.yaml", target)

            self.assertEqual(second["trace_id"], manifest["trace_id"])
            self.assertEqual(extension.read_bytes(), before)

    def test_refuses_to_overwrite_manually_changed_generated_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_repository(Path(temporary))
            hdpgen.generate(FIXTURE / "harness.yaml", target)
            agents = target / "AGENTS.md"
            agents.write_text(agents.read_text(encoding="utf-8") + "\nmanual drift\n", encoding="utf-8")

            with self.assertRaisesRegex(hdpgen.HDPError, "refusing to overwrite"):
                hdpgen.generate(FIXTURE / "harness.yaml", target)

    def test_source_map_and_requirements_record_traceable_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = self.copy_repository(Path(temporary))
            manifest = hdpgen.generate(FIXTURE / "harness.yaml", target)
            source_map = json.loads((target / ".hdp/source-map.json").read_text(encoding="utf-8"))
            requirements = json.loads((target / ".hdp/requirements.json").read_text(encoding="utf-8"))

            self.assertEqual(source_map["trace_id"], manifest["trace_id"])
            self.assertEqual(requirements["trace_id"], manifest["trace_id"])
            self.assertEqual([item["id"] for item in source_map["requirements"]], ["BEHAVIOR-1", "QUALITY-1"])
            self.assertEqual(len(requirements["assumptions"]), 2)
            self.assertEqual(requirements["open_requirements"], [])


class RequiredProcessAndEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.target = self.root / "repository"
        (self.target / "src").mkdir(parents=True)
        (self.target / "tests").mkdir()
        (self.target / "TASK.md").write_text("Keep the smoke test passing.\n", encoding="utf-8")
        (self.target / "src/value.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.target / "tests/test_smoke.py").write_text(
            "import unittest\nfrom src.value import VALUE\n\n"
            "class Smoke(unittest.TestCase):\n"
            "    def test_value(self):\n"
            "        self.assertEqual(VALUE, 1)\n",
            encoding="utf-8",
        )
        self.definition = copy.deepcopy(hdpgen.validate_definition(hdpgen.load_definition(FIXTURE / "harness.yaml")))
        definition_path = self.root / "definition.json"
        definition_path.write_text(json.dumps(self.definition), encoding="utf-8")
        hdpgen.generate(definition_path, self.target)

    def tearDown(self):
        self.temporary.cleanup()

    def test_completion_requires_ordered_process_and_passing_checks(self):
        early = run("python3", "scripts/check_completion.py", cwd=self.target)
        self.assertEqual(early.returncode, 2)
        self.assertIn("missing process evidence", early.stderr)

        wrong_order = run(
            "python3", "scripts/record_step.py", "implement", "--note", "too early", cwd=self.target
        )
        self.assertEqual(wrong_order.returncode, 2)
        self.assertIn("next required step", wrong_order.stderr)

        for step in ("inspect-task", "inspect-tests", "implement"):
            recorded = run(
                "python3", "scripts/record_step.py", step, "--note", f"completed {step}", cwd=self.target
            )
            self.assertEqual(recorded.returncode, 0, recorded.stderr)

        verification = run("python3", "scripts/run_verification.py", cwd=self.target)
        self.assertEqual(verification.returncode, 0, verification.stdout + verification.stderr)
        final_step = run(
            "python3", "scripts/record_step.py", "verify", "--note", "checks passed", cwd=self.target
        )
        self.assertEqual(final_step.returncode, 0, final_step.stderr)
        complete = run("python3", "scripts/check_completion.py", cwd=self.target)
        self.assertEqual(complete.returncode, 0, complete.stdout + complete.stderr)
        payload = json.loads((self.target / "evidence/completion.json").read_text(encoding="utf-8"))
        self.assertTrue(payload["complete"])


class InvalidDefinitionTests(unittest.TestCase):
    def setUp(self):
        self.valid = hdpgen.validate_definition(hdpgen.load_definition(FIXTURE / "harness.yaml"))

    def assert_invalid(self, mutate, expected: str):
        candidate = copy.deepcopy(self.valid)
        mutate(candidate)
        with self.assertRaisesRegex(hdpgen.HDPError, expected):
            hdpgen.validate_definition(candidate)

    def test_missing_required_field(self):
        self.assert_invalid(lambda value: value["metadata"].pop("name"), "missing required field")

    def test_contradictory_write_and_prohibited_paths(self):
        self.assert_invalid(
            lambda value: value["workspace"].update({"prohibited_paths": ["src/private"]}),
            "contradictory writable/prohibited",
        )

    def test_duplicate_verification_id(self):
        self.assert_invalid(
            lambda value: value["verification"]["commands"].append(
                copy.deepcopy(value["verification"]["commands"][0])
            ),
            "duplicate value",
        )

    def test_unknown_check_reference(self):
        self.assert_invalid(
            lambda value: value["verification"]["success_criteria"][0].update({"checks": ["missing"]}),
            "unknown command id",
        )

    def test_blocking_open_requirement_stops_generation(self):
        self.assert_invalid(
            lambda value: value.update(
                {"open_requirements": [{"id": "OPEN-1", "question": "Choose a runtime", "blocking": True}]}
            ),
            "cannot proceed with blocking requirement",
        )

    def test_command_must_use_allowlisted_executable(self):
        self.assert_invalid(
            lambda value: value["verification"]["commands"][0].update({"argv": ["sh", "-c", "true"]}),
            "not allowlisted",
        )


class ProhibitedBoundaryTests(unittest.TestCase):
    def test_path_guard_denies_parent_traversal_and_symlink_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            target = parent / "repository"
            evaluator = parent / "evaluator"
            shutil.copytree(FIXTURE / "repository", target)
            shutil.copytree(FIXTURE / "evaluator", evaluator)
            hdpgen.generate(FIXTURE / "harness.yaml", target)

            allowed = run("python3", "scripts/check_path.py", "--write", "src/new.py", cwd=target)
            traversal = run(
                "python3",
                "scripts/check_path.py",
                "--write",
                "../evaluator/EVALUATOR_CANARY_DO_NOT_COPY.txt",
                cwd=target,
            )
            (target / "src/escape").symlink_to(evaluator, target_is_directory=True)
            symlink_escape = run(
                "python3", "scripts/check_path.py", "--write", "src/escape/hidden.py", cwd=target
            )

            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            self.assertEqual(traversal.returncode, 3)
            self.assertIn("outside repository", traversal.stderr)
            self.assertEqual(symlink_escape.returncode, 3)
            self.assertIn("outside repository", symlink_escape.stderr)

    def test_evaluator_canary_is_absent_from_generated_harness(self):
        marker = (FIXTURE / "evaluator/EVALUATOR_CANARY_DO_NOT_COPY.txt").read_text(encoding="utf-8").strip()
        for path in (FIXTURE / "repository").rglob("*"):
            if path.is_file() and ".git" not in path.parts:
                try:
                    content = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                self.assertNotIn(marker, content, path)

    def test_clean_runner_seals_and_restores_evaluator_boundary(self):
        module_spec = importlib.util.spec_from_file_location(
            "hdp_clean_runner", WORKSTREAM / "tools/run_clean_agent.py"
        )
        self.assertIsNotNone(module_spec)
        self.assertIsNotNone(module_spec.loader)
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            evaluator = Path(temporary) / "evaluator"
            shutil.copytree(FIXTURE / "evaluator", evaluator)
            before = {path: path.stat().st_mode for path in [evaluator, *evaluator.rglob("*")]}

            entries = module.seal_evaluator(evaluator)
            self.assertEqual(evaluator.stat().st_mode & 0o777, 0)
            module.restore_evaluator(entries)

            after = {path: path.stat().st_mode for path in before}
            self.assertEqual(after, before)


class GoldenRegressionTests(unittest.TestCase):
    def test_fixture_generated_tree_matches_golden_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "repository"
            shutil.copytree(FIXTURE / "repository", target)
            manifest = hdpgen.generate(FIXTURE / "harness.yaml", target)
            golden = json.loads((WORKSTREAM / "tests/golden/fixture-managed-hashes.json").read_text(encoding="utf-8"))

            self.assertEqual(manifest["trace_id"], golden["trace_id"])
            self.assertEqual(generated_hashes(target), golden["managed_files"])


if __name__ == "__main__":
    unittest.main()
