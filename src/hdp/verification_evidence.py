"""Deterministically validate release-gating evidence and derive conformance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .conformance import REQUIRED_GATES, canonicalise_conformance
from .diagnostics import HdpGenerationError


EVIDENCE_VERSION = "0.1.0"
REQUIRED_ARTIFACTS = frozenset({
    "local-verification",
    "analyser-coverage",
    "sandbox-probe",
    "behaviour-feature",
    "behaviour-defect-fix",
    "behaviour-refactor",
    "behaviour-policy-block",
    "independent-review",
})
LOCAL_GATES = frozenset({
    "pytest", "validate", "compile", "static-conformance", "analyse",
    "round-trip-diff", "package-ineligible", "verify-release", "tamper-detected",
})
TASK_ARTIFACTS = {
    "feature": "behaviour-feature",
    "defect-fix": "behaviour-defect-fix",
    "refactor": "behaviour-refactor",
    "policy-block": "behaviour-policy-block",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HdpGenerationError(f"{label} is not valid JSON: {exc}") from exc


def _safe_artifact(root: Path, value: Any) -> tuple[str, Path]:
    if not isinstance(value, str) or not value:
        raise HdpGenerationError("verification evidence artifact path must be non-empty")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts or value != relative.as_posix():
        raise HdpGenerationError(f"verification evidence path is unsafe: {value!r}")
    path = root.joinpath(*relative.parts)
    if path.is_symlink() or not path.is_file():
        raise HdpGenerationError(f"verification evidence artifact is missing or unsafe: {value}")
    resolved = path.resolve()
    resolved_root = root.resolve()
    if resolved_root not in resolved.parents:
        raise HdpGenerationError(f"verification evidence escapes its root: {value}")
    return value, resolved


def _local_gate_results(
    value: Any, expected_subject: Mapping[str, Any]
) -> tuple[bool, dict[str, bool]]:
    if not isinstance(value, dict) or value.get("kind") != "LocalVerificationEvidence":
        return False, {}
    gates = value.get("gates")
    if not isinstance(gates, list):
        return False, {}
    results = {
        item.get("id"): item.get("passed") is True
        for item in gates if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    return (
        value.get("passed") is True
        and value.get("subject") == dict(expected_subject)
        and isinstance(value.get("sourceSnapshot"), dict)
        and value["sourceSnapshot"].get("dirty") is False
        and isinstance(value["sourceSnapshot"].get("commit"), str)
        and len(value["sourceSnapshot"]["commit"]) in {40, 64}
        and LOCAL_GATES.issubset(results)
        and all(results[item] for item in LOCAL_GATES),
        results,
    )


def _behaviour_passes(
    value: Any, task: str, expected_subject: Mapping[str, Any]
) -> bool:
    if not isinstance(value, dict):
        return False
    compilation = value.get("compilation")
    results = value.get("results")
    if (
        value.get("passed") is not True
        or value.get("subject") != dict(expected_subject)
        or value.get("definitionOfDoneBehaviouralGate") != "pass"
        or not isinstance(compilation, dict)
        or compilation.get("hir_digest") != expected_subject["hir"]["sha256"]
        or not isinstance(results, list)
    ):
        return False
    harness_results = [
        item for item in results
        if isinstance(item, dict) and item.get("mode") == "harness" and item.get("task") == task
    ]
    if len(harness_results) != 1:
        return False
    result = harness_results[0]
    return (
        result.get("passed") is True
        and result.get("codexExitCode") == 0
        and result.get("evaluatorExitCode") == 0
        and result.get("timedOut") is False
        and result.get("evaluatorBoundaryUnchanged") is True
        and result.get("evaluatorCanaryLeaks") == []
        and result.get("requestedModel") == "gpt-5.6-sol"
        and result.get("requestedReasoningEffort") == "xhigh"
    )


def _coverage_passes(value: Any, expected_subject: Mapping[str, Any]) -> bool:
    return isinstance(value, dict) and (
        value.get("reconstructionStatus") == "implementation-aligned-draft"
        and value.get("sourceMode") == "embedded-generated-source-definition"
        and value.get("structuralStatus") == "pass"
        and value.get("semanticStatus") == "pass"
        and value.get("unknownRequiredFamilies") == []
        and value.get("subject") == dict(expected_subject)
    )


def _sandbox_passes(value: Any, expected_subject: Mapping[str, Any]) -> bool:
    return isinstance(value, dict) and (
        value.get("kind") == "CodexSandboxProbe"
        and value.get("subject") == dict(expected_subject)
        and value.get("passed") is True
        and value.get("requestedModel") == "gpt-5.6-sol"
        and value.get("requestedReasoningEffort") == "xhigh"
        and isinstance(value.get("probes"), list)
        and {item.get("id") for item in value["probes"] if isinstance(item, dict)}
        == {"outside-workspace-read", "network-tcp-connect", "inside-workspace-write-read"}
        and all(item.get("passed") is True for item in value["probes"] if isinstance(item, dict))
    )


def _review_passes(value: Any, expected_subject: Mapping[str, Any]) -> bool:
    return isinstance(value, dict) and (
        value.get("kind") == "IndependentAdversarialReview"
        and value.get("subject") == dict(expected_subject)
        and value.get("reviewerModel") == "gpt-5.6-sol"
        and value.get("reasoningEffort") == "xhigh"
        and value.get("status") in {"pass", "remediated"}
        and value.get("unresolvedCritical") == []
        and value.get("unresolvedHigh") == []
    )


def validate_verification_bundle(
    bundle_path: Path,
    expected_subject: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Path]]:
    """Validate content-addressed raw evidence and derive a closed gate result."""

    if bundle_path.is_symlink() or not bundle_path.is_file():
        raise HdpGenerationError(f"verification evidence bundle is missing or unsafe: {bundle_path}")
    value = _read_json(bundle_path, "verification evidence bundle")
    if not isinstance(value, dict) or set(value) != {
        "schemaVersion", "kind", "subject", "artifacts", "retainedFailures",
    }:
        raise HdpGenerationError("verification evidence bundle has invalid fields")
    if value.get("schemaVersion") != EVIDENCE_VERSION or value.get("kind") != "FactoryVerificationEvidence":
        raise HdpGenerationError("unsupported verification evidence bundle")
    if value.get("subject") != dict(expected_subject):
        raise HdpGenerationError("verification evidence subject does not match the release subject")
    if not isinstance(value.get("retainedFailures"), list):
        raise HdpGenerationError("verification evidence retainedFailures must be an array")
    records = value.get("artifacts")
    if not isinstance(records, list):
        raise HdpGenerationError("verification evidence artifacts must be an array")

    root = bundle_path.parent
    paths: dict[str, Path] = {}
    values: dict[str, Any] = {}
    seen_paths: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != {"id", "path", "sha256"}:
            raise HdpGenerationError("verification evidence artifact record is invalid")
        artifact_id = record.get("id")
        if not isinstance(artifact_id, str) or artifact_id in paths:
            raise HdpGenerationError("verification evidence artifact ID is invalid or duplicated")
        relative, path = _safe_artifact(root, record.get("path"))
        if path == bundle_path.resolve():
            raise HdpGenerationError("verification evidence bundle cannot reference itself")
        if relative in seen_paths:
            raise HdpGenerationError("verification evidence artifact path is duplicated")
        seen_paths.add(relative)
        if record.get("sha256") != _sha256(path):
            raise HdpGenerationError(f"verification evidence digest mismatch: {relative}")
        paths[artifact_id] = path
        values[artifact_id] = _read_json(path, f"verification evidence {artifact_id}")
    if set(paths) != REQUIRED_ARTIFACTS:
        raise HdpGenerationError(
            "verification evidence artifacts must be the exact required set; "
            f"missing={sorted(REQUIRED_ARTIFACTS - set(paths))}, "
            f"unknown={sorted(set(paths) - REQUIRED_ARTIFACTS)}"
        )

    local_pass, local_gates = _local_gate_results(
        values["local-verification"], expected_subject
    )
    behaviour_pass = all(
        _behaviour_passes(
            values[artifact_id], task, expected_subject
        )
        for task, artifact_id in TASK_ARTIFACTS.items()
    )
    analyser_pass = local_pass and _coverage_passes(
        values["analyser-coverage"], expected_subject
    )
    sandbox_pass = _sandbox_passes(values["sandbox-probe"], expected_subject)
    review_pass = _review_passes(values["independent-review"], expected_subject)
    gate_passes = {
        "input-integrity": local_pass and local_gates.get("validate", False),
        "semantic-hir": local_pass and local_gates.get("validate", False),
        "compiler": local_pass and local_gates.get("compile", False),
        "codex-static": local_pass and local_gates.get("static-conformance", False),
        "security": local_pass and sandbox_pass,
        "behaviour": behaviour_pass,
        "analyser": analyser_pass and local_gates.get("analyse", False),
        "round-trip": analyser_pass and local_gates.get("round-trip-diff", False),
        "release": local_pass and local_gates.get("verify-release", False)
        and local_gates.get("tamper-detected", False),
        "independent-review": review_pass,
    }
    bundle_digest = _sha256(bundle_path)
    raw = {
        "conformanceVersion": "0.1.0",
        "subject": dict(expected_subject),
        "gates": [
            {
                "id": gate_id,
                "status": "pass" if gate_passes[gate_id] else "fail",
                "evidenceDigest": bundle_digest,
            }
            for gate_id in REQUIRED_GATES
        ],
        "status": "not-run",
        "releaseEligible": False,
    }
    return canonicalise_conformance(raw, expected_subject=expected_subject), paths
