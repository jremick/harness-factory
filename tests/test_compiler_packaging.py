import copy
import hashlib
import json
import mimetypes
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from hdp.adapters import CodexAdapter
from hdp.bindings import load_codex_binding
from hdp.cli import app
from hdp.compiler import (
    CompilationResult, compare_hdp, compile_hdp, validate_and_normalise,
)
from hdp.conformance import (
    REQUIRED_GATES, binding_digest, canonicalise_conformance, stable_binding_identity,
)
from hdp.diagnostics import HdpGenerationError
from hdp.hir import HIR
from hdp.io import dump_yaml, load_document
from hdp.packaging import package_release, verify_release


ROOT = Path(__file__).parents[1]
EXAMPLE = ROOT / "examples/software-development/hdp.yaml"
BINDING = ROOT / "examples/software-development/bindings/codex.yaml"


def hashes(manifest: dict) -> dict[str, str]:
    return {item["path"]: item["sha256"] for item in manifest["artifacts"]}


def passing_conformance_for(harness: Path) -> dict:
    binding_model = load_codex_binding(BINDING)
    hir = validate_and_normalise(
        EXAMPLE, binding_ref=stable_binding_identity(binding_model)
    )
    manifest = load_document(harness / ".hdp/manifest.json")
    records = []
    for path in sorted(harness.rglob("*")):
        relative = path.relative_to(harness)
        if any(part in {"__pycache__", ".pytest_cache", ".git"} for part in relative.parts):
            continue
        if path.is_file():
            mode = path.stat().st_mode
            records.append({
                "path": relative.as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size": path.stat().st_size,
                "executable": bool(mode & 0o111),
                "mediaType": mimetypes.guess_type(relative.as_posix())[0] or "application/octet-stream",
            })
    harness_digest = hashlib.sha256(
        json.dumps(records, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    evidence_digest = hashlib.sha256(b"test evidence").hexdigest()
    return {
        "conformanceVersion": "0.1.0",
        "subject": {
            "definition": {"id": manifest["source"]["id"], "sha256": hir.source_digest},
            "hir": {"sha256": hir.digest()},
            "binding": {"target": "codex", "sha256": binding_digest(binding_model)},
            "harness": {"sha256": harness_digest},
        },
        "gates": [
            {"id": gate_id, "status": "pass", "evidenceDigest": evidence_digest}
            for gate_id in REQUIRED_GATES
        ],
        "status": "pass",
        "releaseEligible": True,
    }


def verification_bundle_for(harness: Path, root: Path) -> Path:
    evidence = root / "evidence"
    evidence.mkdir()
    subject = passing_conformance_for(harness)["subject"]
    local = {
        "kind": "LocalVerificationEvidence",
        "passed": True,
        "gates": [
            {"id": gate_id, "passed": True}
            for gate_id in (
                "pytest", "validate", "compile", "static-conformance", "analyse",
                "round-trip-diff", "package-ineligible", "verify-release", "tamper-detected",
            )
        ],
    }
    coverage = {
        "reconstructionStatus": "implementation-aligned-draft",
        "sourceMode": "embedded-generated-source-definition",
        "structuralStatus": "pass",
        "semanticStatus": "pass",
        "unknownRequiredFamilies": [],
    }
    sandbox = {
        "kind": "CodexSandboxProbe",
        "passed": True,
        "requestedModel": "gpt-5.6-sol",
        "requestedReasoningEffort": "xhigh",
        "probes": [
            {"id": item, "passed": True}
            for item in (
                "outside-workspace-read", "network-tcp-connect",
                "inside-workspace-write-read",
            )
        ],
    }
    review = {
        "kind": "IndependentAdversarialReview",
        "reviewerModel": "gpt-5.6-sol",
        "reasoningEffort": "xhigh",
        "status": "pass",
        "unresolvedCritical": [],
        "unresolvedHigh": [],
    }
    documents = {
        "local-verification": local,
        "analyser-coverage": coverage,
        "sandbox-probe": sandbox,
        "independent-review": review,
    }
    for task in ("feature", "defect-fix", "refactor", "policy-block"):
        documents[f"behaviour-{task}"] = {
            "passed": True,
            "definitionOfDoneBehaviouralGate": "pass",
            "compilation": {"hir_digest": subject["hir"]["sha256"]},
            "results": [{
                "task": task,
                "mode": "harness",
                "passed": True,
                "codexExitCode": 0,
                "evaluatorExitCode": 0,
                "timedOut": False,
                "evaluatorBoundaryUnchanged": True,
                "evaluatorCanaryLeaks": [],
                "requestedModel": "gpt-5.6-sol",
                "requestedReasoningEffort": "xhigh",
            }],
        }
    artifacts = []
    for artifact_id, document in sorted(documents.items()):
        path = evidence / f"{artifact_id}.json"
        path.write_text(json.dumps(document, sort_keys=True))
        artifacts.append({
            "id": artifact_id,
            "path": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    bundle = evidence / "bundle-source.json"
    bundle.write_text(json.dumps({
        "schemaVersion": "0.1.0",
        "kind": "FactoryVerificationEvidence",
        "subject": subject,
        "artifacts": artifacts,
        "retainedFailures": [],
    }, sort_keys=True))
    return bundle


def test_compiler_is_reproducible_and_emits_codex_surface() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        first = compile_hdp(EXAMPLE, BINDING, root / "one")
        second = compile_hdp(EXAMPLE, BINDING, root / "two")
        assert first.status == second.status == "pass"
        assert first.hir_digest == second.hir_digest
        assert "/Users/" not in load_document(root / "one/.hdp/hir.json")["entities"][-1].get("binding_ref", "")
        assert hashes(first.manifest) == hashes(second.manifest)
        assert (root / "one/.codex/config.toml").is_file()
        assert list((root / "one/.agents/skills").glob("*/agents/openai.yaml"))
        assert (root / "one/HarnessCard.md").is_file()
        manifest = load_document(root / "one/.hdp/manifest.json")
        source_map = load_document(root / "one/.hdp/source-map.json")
        assert all(item["sourceFields"] for item in manifest["artifacts"])
        assert {item["path"] for item in manifest["artifacts"]} == set(source_map)


def test_hir_digest_uses_binding_content_identity_not_local_path() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        first_binding = root / "one/binding.yaml"
        second_binding = root / "elsewhere/binding.yaml"
        for path in (first_binding, second_binding):
            path.parent.mkdir(parents=True)
            path.write_bytes(BINDING.read_bytes())
        first = compile_hdp(EXAMPLE, first_binding, root / "first")
        second = compile_hdp(EXAMPLE, second_binding, root / "second")
        assert first.hir_digest == second.hir_digest
        embedded = load_document(root / "first/.hdp/hir.json")
        adapter = next(item for item in embedded["entities"] if item["kind"] == "adapter_ref")
        assert adapter["binding_ref"].startswith("target-binding:codex@sha256:")
        assert str(first_binding) not in json.dumps(embedded)


def test_compile_cli_exits_nonzero_when_compilation_status_fails() -> None:
    failed = CompilationResult(
        status="fail",
        output="generated",
        hir_digest="0" * 64,
        manifest={"artifacts": []},
        stages=(),
    )
    with patch("hdp.cli.compile_hdp", return_value=failed):
        result = CliRunner().invoke(
            app,
            ["compile", str(EXAMPLE), "--binding", str(BINDING), "--output", "generated"],
        )
    assert result.exit_code == 2
    assert '"status": "fail"' in result.stdout


def test_command_recorder_denies_unknown_executable_and_strips_fake_secret() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        target = Path(temporary) / "generated"
        compile_hdp(EXAMPLE, BINDING, target)
        denied = subprocess.run(
            ["python3", "scripts/harnessctl.py", "run", "--", "/bin/echo", "bad"],
            cwd=target, capture_output=True, text=True, check=False,
        )
        assert denied.returncode == 77
        environment = os.environ.copy()
        environment["HDP_FAKE_SECRET"] = "HDP_SECRET_CANARY_48391"
        checked = subprocess.run(
            ["python3", "scripts/harnessctl.py", "run", "--", "python3", "-c",
             "import os; print(os.environ.get('HDP_FAKE_SECRET', 'absent'))"],
            cwd=target, capture_output=True, text=True, check=False, env=environment,
        )
        assert checked.returncode == 0
        assert checked.stdout.strip() == "absent"


def test_binding_must_cover_command_capabilities() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        binding = load_document(BINDING)
        binding["commandBindings"].pop("TOOL-GIT")
        path = Path(temporary) / "binding.yaml"
        path.write_text(dump_yaml(binding))
        with pytest.raises(ValueError, match="missing=.*TOOL-GIT"):
            compile_hdp(EXAMPLE, path, Path(temporary) / "generated")


def test_binding_must_declare_outer_enforcement_boundaries() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        binding = load_document(BINDING)
        binding["externallyEnforcedResources"].remove("network")
        path = Path(temporary) / "binding.yaml"
        path.write_text(dump_yaml(binding))
        with pytest.raises(ValueError, match="missing=.*network"):
            compile_hdp(EXAMPLE, path, Path(temporary) / "generated")


def test_static_conformance_rejects_secret_pattern_in_generated_artifact() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        target = Path(temporary) / "generated"
        result = compile_hdp(EXAMPLE, BINDING, target)
        card = target / "HarnessCard.md"
        card.write_text(card.read_text() + "\napi_key = sk-proj-abcdefghijklmnopqrstuvwxyz123456\n")
        hir = HIR.model_validate(load_document(target / ".hdp/hir.json"))
        conformance = CodexAdapter(load_codex_binding(BINDING)).static_check(target, hir)
        secret_check = next(item for item in conformance.checks if item["id"] == "generated-secret-patterns")
        assert secret_check["passed"] is False
        assert secret_check["findings"][0]["path"] == "HarnessCard.md"
        assert "abcdefghijklmnopqrstuvwxyz" not in json.dumps(secret_check)


def test_package_verifies_and_tamper_fails() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        harness = root / "harness"
        release = root / "release"
        compile_hdp(EXAMPLE, BINDING, harness)
        packaged = package_release(harness, EXAMPLE, BINDING, release)
        assert packaged["status"] == "pass"
        assert packaged["releaseEligible"] is False
        assert verify_release(release)["verified"] is True

        agents = release / "payload/harness/AGENTS.md"
        agents.write_text(agents.read_text() + "tampered\n")
        result = verify_release(release)
        assert result["verified"] is False
        assert any("digest mismatch" in item for item in result["errors"])


def test_release_eligibility_is_derived_from_recomputed_evidence() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        harness = root / "harness"
        compile_hdp(EXAMPLE, BINDING, harness)
        conformance_path = verification_bundle_for(harness, root)
        packaged = package_release(
            harness, EXAMPLE, BINDING, root / "release", conformance=conformance_path,
        )
        assert packaged["releaseEligible"] is True
        assert verify_release(root / "release")["releaseEligible"] is True

        local_path = root / "evidence/local-verification.json"
        local = json.loads(local_path.read_text())
        local["passed"] = False
        local_path.write_text(json.dumps(local, sort_keys=True))
        bundle = json.loads(conformance_path.read_text())
        local_record = next(
            item for item in bundle["artifacts"] if item["id"] == "local-verification"
        )
        local_record["sha256"] = hashlib.sha256(local_path.read_bytes()).hexdigest()
        conformance_path.write_text(json.dumps(bundle, sort_keys=True))
        forged_release = root / "forged-release"
        result = package_release(
            harness, EXAMPLE, BINDING, forged_release, conformance=conformance_path,
        )
        assert result["releaseEligible"] is False
        canonical = load_document(forged_release / "payload/conformance.json")
        assert canonical["status"] == "fail"
        assert canonical["releaseEligible"] is False


@pytest.mark.parametrize("mutation", ["subject", "missing-gate", "duplicate-gate", "extra-field"])
def test_package_rejects_unbound_or_open_conformance(mutation: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        harness = root / "harness"
        compile_hdp(EXAMPLE, BINDING, harness)
        conformance = passing_conformance_for(harness)
        if mutation == "subject":
            conformance["subject"]["binding"]["sha256"] = "0" * 64
        elif mutation == "missing-gate":
            conformance["gates"].pop()
        elif mutation == "duplicate-gate":
            conformance["gates"][-1] = copy.deepcopy(conformance["gates"][0])
        else:
            conformance["claimedBy"] = "caller"
        path = root / "conformance.json"
        path.write_text(json.dumps(conformance))
        with pytest.raises(HdpGenerationError, match="verification evidence"):
            package_release(harness, EXAMPLE, BINDING, root / "release", conformance=path)


def test_comparative_attribution_requires_the_conditional_baseline_gate() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        harness = Path(temporary) / "harness"
        compile_hdp(EXAMPLE, BINDING, harness)
        conformance = passing_conformance_for(harness)
        conformance["comparativeAttribution"] = True
        with pytest.raises(HdpGenerationError, match="baseline"):
            canonicalise_conformance(
                conformance, expected_subject=conformance["subject"]
            )
        conformance["gates"].append({
            "id": "baseline",
            "status": "pass",
            "evidenceDigest": hashlib.sha256(b"baseline evidence").hexdigest(),
        })
        result = canonicalise_conformance(
            conformance, expected_subject=conformance["subject"]
        )
        assert result["releaseEligible"] is True


@pytest.mark.parametrize("mismatch", ["definition", "binding"])
def test_package_rejects_definition_or_binding_mismatch(mismatch: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        harness = root / "harness"
        compile_hdp(EXAMPLE, BINDING, harness)
        definition = EXAMPLE
        binding = BINDING
        if mismatch == "definition":
            changed = load_document(EXAMPLE)
            changed["purpose"]["nonGoals"][0] = "Different semantics."
            definition = root / "different.yaml"
            definition.write_text(dump_yaml(changed))
        else:
            changed = load_document(BINDING)
            changed["settings"]["model"] = "different-model"
            binding = root / "different-binding.yaml"
            binding.write_text(dump_yaml(changed))
        with pytest.raises(HdpGenerationError, match="does not match"):
            package_release(harness, definition, binding, root / "release")


@pytest.mark.parametrize(
    "relative",
    [".codex/config.toml", ".hdp/hir.json", ".hdp/manifest.json", "scripts/extra-control.py"],
)
def test_package_rejects_modified_or_untracked_generated_controls(relative: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        harness = root / "harness"
        compile_hdp(EXAMPLE, BINDING, harness)
        path = harness / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(path.read_text() + "tamper\n" if path.exists() else "pass\n")
        with pytest.raises(
            HdpGenerationError, match="control|match|manifest|generated harness HIR"
        ):
            package_release(harness, EXAMPLE, BINDING, root / "release")


def test_semantic_diff_round_trip_is_exact() -> None:
    result = compare_hdp(EXAMPLE, EXAMPLE)
    assert result["parity"] is True
    assert result["entityDifferences"] == []


def test_semantic_diff_detects_material_canonical_semantics_without_hir_entity_change() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        changed = load_document(EXAMPLE)
        changed["purpose"]["nonGoals"][0] = "A materially different non-goal."
        path = Path(temporary) / "changed.yaml"
        path.write_text(dump_yaml(changed))
        result = compare_hdp(EXAMPLE, path)
        assert result["parity"] is False
        assert result["entityDifferences"] == []
        assert "/purpose/nonGoals/0" in result["canonicalSemanticDifferences"]
