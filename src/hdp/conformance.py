"""Closed, deterministic conformance records and subject bindings."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping

from .bindings import CodexBinding
from .diagnostics import HdpGenerationError
from .io import canonical_json


CONFORMANCE_VERSION = "0.1.0"
REQUIRED_GATES: tuple[str, ...] = (
    "input-integrity",
    "semantic-hir",
    "compiler",
    "codex-static",
    "security",
    "behaviour",
    "analyser",
    "round-trip",
    "release",
    "independent-review",
)
CONDITIONAL_BASELINE_GATE = "baseline"
GATE_STATUSES = frozenset({"pass", "fail", "blocked", "not-run", "inconclusive"})
_SHA256 = re.compile(r"[0-9a-f]{64}")


def sha256_canonical(value: Any) -> str:
    """Return the SHA-256 identity of a canonical JSON value."""

    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def binding_document(binding: CodexBinding) -> dict[str, Any]:
    return binding.model_dump(mode="json", by_alias=True)


def binding_digest(binding: CodexBinding) -> str:
    return sha256_canonical(binding_document(binding))


def stable_binding_identity(binding: CodexBinding) -> str:
    """Identify a binding by target and content, never by a machine-local path."""

    return f"target-binding:{binding.target}@sha256:{binding_digest(binding)}"


def declares_comparative_attribution(document: Mapping[str, Any]) -> bool:
    """Recognise only explicit comparative-attribution declarations.

    The v0.1 schema has no core comparative-attribution field. This recognises a
    future core boolean or a namespaced extension without inferring intent from
    prose or from the mere presence of an operational monitoring baseline.
    """

    direct = document.get("comparativeAttribution")
    if direct is True:
        return True
    extensions = document.get("extensions")
    if not isinstance(extensions, Mapping):
        return False
    declaration = extensions.get("x-hdp-comparative-attribution")
    if declaration is True:
        return True
    return isinstance(declaration, Mapping) and (
        declaration.get("enabled") is True or declaration.get("required") is True
    )


def subject_bindings(
    *,
    definition_id: str,
    definition_digest: str,
    hir_digest: str,
    binding_target: str,
    binding_digest_value: str,
    harness_digest: str,
) -> dict[str, Any]:
    for label, digest in (
        ("definition", definition_digest),
        ("HIR", hir_digest),
        ("binding", binding_digest_value),
        ("harness", harness_digest),
    ):
        if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
            raise HdpGenerationError(f"invalid {label} subject SHA-256 digest")
    return {
        "definition": {"id": definition_id, "sha256": definition_digest},
        "hir": {"sha256": hir_digest},
        "binding": {"target": binding_target, "sha256": binding_digest_value},
        "harness": {"sha256": harness_digest},
    }


def empty_conformance(
    subject: Mapping[str, Any], *, comparative_attribution: bool = False
) -> dict[str, Any]:
    gates = [*REQUIRED_GATES]
    if comparative_attribution:
        gates.append(CONDITIONAL_BASELINE_GATE)
    value: dict[str, Any] = {
        "conformanceVersion": CONFORMANCE_VERSION,
        "subject": dict(subject),
        "gates": [
            {"id": gate_id, "status": "not-run", "evidenceDigest": None}
            for gate_id in gates
        ],
        "status": "not-run",
        "releaseEligible": False,
    }
    if comparative_attribution:
        value["comparativeAttribution"] = True
    return value


def _derived_status(statuses: list[str]) -> str:
    if statuses and all(status == "pass" for status in statuses):
        return "pass"
    for blocking in ("fail", "blocked", "inconclusive"):
        if blocking in statuses:
            return blocking
    return "not-run"


def canonicalise_conformance(
    value: Any,
    *,
    expected_subject: Mapping[str, Any],
    comparative_attribution_required: bool = False,
) -> dict[str, Any]:
    """Validate a closed result and deterministically derive its decision fields."""

    if not isinstance(value, dict):
        raise HdpGenerationError("conformance result must be an object")
    base_keys = {
        "conformanceVersion", "subject", "gates", "status", "releaseEligible",
    }
    allowed_keys = base_keys | {"comparativeAttribution"}
    unknown = set(value) - allowed_keys
    missing = base_keys - set(value)
    if missing or unknown:
        raise HdpGenerationError(
            "conformance result has invalid fields; "
            f"missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    if value.get("conformanceVersion") != CONFORMANCE_VERSION:
        raise HdpGenerationError("unsupported conformance result version")
    if not isinstance(value.get("status"), str) or value["status"] not in GATE_STATUSES:
        raise HdpGenerationError("conformance status is invalid")
    if not isinstance(value.get("releaseEligible"), bool):
        raise HdpGenerationError("conformance releaseEligible must be boolean")
    if "comparativeAttribution" in value and not isinstance(value["comparativeAttribution"], bool):
        raise HdpGenerationError("conformance comparativeAttribution must be boolean")
    comparative = comparative_attribution_required or value.get("comparativeAttribution") is True
    if comparative_attribution_required and value.get("comparativeAttribution") is not True:
        raise HdpGenerationError(
            "definition declares comparative attribution but conformance does not bind its baseline"
        )

    subject = value.get("subject")
    if not isinstance(subject, dict) or subject != dict(expected_subject):
        raise HdpGenerationError("conformance subject does not match harness, definition, HIR, and binding")
    expected_subject_keys = {"definition", "hir", "binding", "harness"}
    if set(subject) != expected_subject_keys:
        raise HdpGenerationError("conformance subject bindings must be closed")
    nested_subject_keys = {
        "definition": {"id", "sha256"},
        "hir": {"sha256"},
        "binding": {"target", "sha256"},
        "harness": {"sha256"},
    }
    for name, keys in nested_subject_keys.items():
        if not isinstance(subject[name], dict) or set(subject[name]) != keys:
            raise HdpGenerationError(f"conformance {name} subject binding must be closed")

    gates = value.get("gates")
    if not isinstance(gates, list):
        raise HdpGenerationError("conformance gates must be an array")
    expected_gate_ids = set(REQUIRED_GATES)
    if comparative:
        expected_gate_ids.add(CONDITIONAL_BASELINE_GATE)
    seen: set[str] = set()
    canonical_gates: list[dict[str, Any]] = []
    for gate in gates:
        if not isinstance(gate, dict) or set(gate) != {"id", "status", "evidenceDigest"}:
            raise HdpGenerationError(
                "each conformance gate must contain only id, status, and evidenceDigest"
            )
        gate_id = gate.get("id")
        status = gate.get("status")
        evidence_digest = gate.get("evidenceDigest")
        if not isinstance(gate_id, str) or gate_id in seen:
            raise HdpGenerationError(f"conformance gate ID is invalid or duplicated: {gate_id!r}")
        seen.add(gate_id)
        if not isinstance(status, str) or status not in GATE_STATUSES:
            raise HdpGenerationError(f"conformance gate {gate_id!r} has invalid status")
        if evidence_digest is not None and (
            not isinstance(evidence_digest, str) or _SHA256.fullmatch(evidence_digest) is None
        ):
            raise HdpGenerationError(f"conformance gate {gate_id!r} has invalid evidence digest")
        if status == "pass" and evidence_digest is None:
            raise HdpGenerationError(f"passing conformance gate {gate_id!r} requires evidence digest")
        canonical_gates.append({
            "id": gate_id, "status": status, "evidenceDigest": evidence_digest,
        })
    if seen != expected_gate_ids:
        raise HdpGenerationError(
            "conformance gates must be the exact canonical set; "
            f"missing={sorted(expected_gate_ids - seen)}, unknown={sorted(seen - expected_gate_ids)}"
        )

    canonical_gates.sort(key=lambda item: (
        (*REQUIRED_GATES, CONDITIONAL_BASELINE_GATE).index(item["id"])
    ))
    statuses = [item["status"] for item in canonical_gates]
    derived_status = _derived_status(statuses)
    release_eligible = derived_status == "pass"
    result: dict[str, Any] = {
        "conformanceVersion": CONFORMANCE_VERSION,
        "subject": dict(expected_subject),
        "gates": canonical_gates,
        "status": derived_status,
        "releaseEligible": release_eligible,
    }
    if comparative:
        result["comparativeAttribution"] = True
    return result
