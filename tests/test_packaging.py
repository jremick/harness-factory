import copy
import json
import tempfile
import unittest
from pathlib import Path

from hdp.compiler import compile_hdp
from hdp.packaging import package_release, verify_release


ROOT = Path(__file__).resolve().parents[1]
DEFINITION = ROOT / "examples" / "software-development" / "hdp.yaml"
BINDING = ROOT / "examples" / "software-development" / "bindings" / "codex.yaml"


class PackagingTests(unittest.TestCase):
    def make_release(self, parent: Path) -> Path:
        harness = parent / "harness"
        release = parent / "release"
        compile_hdp(DEFINITION, BINDING, harness)
        package_release(harness, DEFINITION, BINDING, release)
        self.assertTrue(verify_release(release)["verified"])
        return release

    def test_payload_tamper_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            release = self.make_release(Path(temporary))
            agents = release / "payload" / "harness" / "AGENTS.md"
            agents.write_text(agents.read_text(encoding="utf-8") + "tamper\n", encoding="utf-8")
            self.assertFalse(verify_release(release)["verified"])

    def test_manifest_metadata_and_eligibility_tamper_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            release = self.make_release(Path(temporary))
            manifest_path = release / "release-manifest.json"
            original = json.loads(manifest_path.read_text(encoding="utf-8"))
            for field, value in (
                ("manifestVersion", "999"),
                ("digestAlgorithm", "md5"),
                ("releaseEligible", True),
            ):
                manifest = copy.deepcopy(original)
                manifest[field] = value
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                self.assertFalse(verify_release(release)["verified"], field)
            manifest = copy.deepcopy(original)
            manifest["files"][0]["mediaType"] = "application/x-forged"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertFalse(verify_release(release)["verified"])

    def test_attestation_envelope_and_predicate_tamper_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            release = self.make_release(Path(temporary))
            for name, mutation in (
                ("build.intoto.json", lambda item: item.update({"_type": "forged"})),
                (
                    "build.intoto.json",
                    lambda item: item["predicate"]["builder"].update({"id": "forged"}),
                ),
                (
                    "tests.intoto.json",
                    lambda item: item.update({"predicateType": "forged"}),
                ),
                (
                    "tests.intoto.json",
                    lambda item: item["predicate"].update({"authenticated": True}),
                ),
            ):
                path = release / "attestations" / name
                original = json.loads(path.read_text(encoding="utf-8"))
                changed = copy.deepcopy(original)
                mutation(changed)
                path.write_text(json.dumps(changed), encoding="utf-8")
                result = verify_release(release)
                self.assertFalse(result["verified"], (name, changed))
                self.assertTrue(any("attestation" in error for error in result["errors"]))
                path.write_text(json.dumps(original), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
