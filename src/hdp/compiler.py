"""End-to-end HDP compiler orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from .adapters import CodexAdapter
from .bindings import load_codex_binding
from .conformance import stable_binding_identity
from .diagnostics import HdpGenerationError
from .hir import HIR
from .io import load_document
from .normalise import normalise_hdp
from .schema_validation import structural_diagnostics
from .semantic_validation import semantic_diagnostics


class StageResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    stage: str
    status: Literal["pass", "fail", "blocked", "not-run", "inconclusive"]
    details: dict[str, Any]


class CompilationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    status: Literal["pass", "fail"]
    output: str
    hir_digest: str
    manifest: dict[str, Any]
    stages: tuple[StageResult, ...]


def _compilable_document(document: dict[str, Any]) -> dict[str, Any]:
    """Remove analyser-only evidence metadata from canonical build semantics."""

    value = document.copy()
    extensions = value.get("extensions")
    if isinstance(extensions, dict) and "x-hdp-reconstruction" in extensions:
        extensions = extensions.copy()
        extensions.pop("x-hdp-reconstruction", None)
        value["extensions"] = extensions
    return value


def validate_and_normalise(definition_path: Path, *, binding_ref: str | None = None) -> HIR:
    document = load_document(definition_path)
    diagnostics = structural_diagnostics(document)
    if not diagnostics:
        diagnostics.extend(semantic_diagnostics(document, definition_path.parent))
    if diagnostics:
        summary = "; ".join(
            f"{item.code} {item.instance_path or '/'}: {item.message}"
            for item in diagnostics[:12]
        )
        raise HdpGenerationError(f"definition is invalid: {summary}")
    return normalise_hdp(_compilable_document(document), binding_ref=binding_ref)


def compile_hdp(
    definition_path: Path,
    binding_path: Path,
    output: Path,
    *,
    force_generated: bool = False,
) -> CompilationResult:
    stages: list[StageResult] = []
    document = load_document(definition_path)
    stages.append(StageResult(stage="ingest", status="pass", details={"source": str(definition_path)}))
    structural = structural_diagnostics(document)
    stages.append(StageResult(
        stage="schema-validation", status="fail" if structural else "pass",
        details={"diagnostics": [item.to_dict() for item in structural]},
    ))
    if structural:
        raise HdpGenerationError("definition failed schema validation")
    semantic = semantic_diagnostics(document, definition_path.parent)
    stages.append(StageResult(
        stage="semantic-validation", status="fail" if semantic else "pass",
        details={"diagnostics": [item.to_dict() for item in semantic]},
    ))
    if semantic:
        raise HdpGenerationError("definition failed semantic validation")
    binding = load_codex_binding(binding_path)
    hir = normalise_hdp(
        _compilable_document(document),
        binding_ref=stable_binding_identity(binding),
    )
    stages.append(StageResult(
        stage="normalisation", status="pass",
        details={"hirVersion": hir.hir_version, "hirDigest": hir.digest()},
    ))
    adapter = CodexAdapter(binding)
    plan = adapter.plan(hir)
    stages.append(StageResult(
        stage="compilation-planning", status="pass",
        details={"adapter": adapter.name, "adapterVersion": adapter.version, "artifacts": len(plan.artifacts)},
    ))
    stages.append(StageResult(
        stage="bounded-assisted-synthesis", status="pass",
        details={"requests": 0, "authority": "none"},
    ))
    manifest = adapter.render(hir, output, force_generated=force_generated)
    stages.append(StageResult(
        stage="deterministic-rendering", status="pass",
        details={"artifactCount": len(manifest["artifacts"])},
    ))
    conformance = adapter.static_check(output, hir)
    stages.append(StageResult(
        stage="static-conformance", status=conformance.status,
        details={"checks": list(conformance.checks)},
    ))
    stages.extend([
        StageResult(
            stage="sandboxed-behavioural-conformance", status="not-run",
            details={"reason": "run explicitly with the target task runner"},
        ),
        StageResult(
            stage="packaging", status="not-run",
            details={"reason": "run hdp package after behavioural evidence is available"},
        ),
        StageResult(
            stage="attestation", status="not-run",
            details={"reason": "created by hdp package"},
        ),
    ])
    return CompilationResult(
        status="pass" if conformance.status == "pass" else "fail",
        output=str(output.resolve()), hir_digest=hir.digest(), manifest=manifest,
        stages=tuple(stages),
    )


def compare_hdp(left: Path, right: Path) -> dict[str, Any]:
    left_hir = validate_and_normalise(left)
    right_hir = validate_and_normalise(right)

    def projection(hir: HIR) -> dict[str, Any]:
        return {
            "entities": {
                item.id: item.model_dump(mode="json", exclude={"source_pointers"})
                for item in hir.entities
            },
            "relations": {
                item.id: item.model_dump(mode="json", exclude={"source_pointers"})
                for item in hir.relations
            },
        }

    left_projection = projection(left_hir)
    right_projection = projection(right_hir)
    entity_ids = set(left_projection["entities"]) | set(right_projection["entities"])
    relation_ids = set(left_projection["relations"]) | set(right_projection["relations"])
    entity_differences = [
        item for item in sorted(entity_ids)
        if left_projection["entities"].get(item) != right_projection["entities"].get(item)
    ]
    relation_differences = [
        item for item in sorted(relation_ids)
        if left_projection["relations"].get(item) != right_projection["relations"].get(item)
    ]

    def semantic_paths(left_value: Any, right_value: Any, pointer: str = "") -> list[str]:
        if isinstance(left_value, dict) and isinstance(right_value, dict):
            differences: list[str] = []
            for key in sorted(set(left_value) | set(right_value)):
                escaped = str(key).replace("~", "~0").replace("/", "~1")
                differences.extend(semantic_paths(
                    left_value.get(key, _MISSING), right_value.get(key, _MISSING),
                    f"{pointer}/{escaped}",
                ))
            return differences
        if isinstance(left_value, list) and isinstance(right_value, list):
            differences = []
            for index in range(max(len(left_value), len(right_value))):
                left_item = left_value[index] if index < len(left_value) else _MISSING
                right_item = right_value[index] if index < len(right_value) else _MISSING
                differences.extend(semantic_paths(
                    left_item, right_item, f"{pointer}/{index}",
                ))
            return differences
        return [] if left_value == right_value else [pointer or "/"]

    def parity_semantics(hir: HIR) -> dict[str, Any]:
        value = hir.canonical_semantics.copy()
        extensions = value.get("extensions")
        if isinstance(extensions, dict):
            extensions = extensions.copy()
            extensions.pop("x-hdp-reconstruction", None)
            value["extensions"] = extensions
        return value

    canonical_differences = semantic_paths(
        parity_semantics(left_hir), parity_semantics(right_hir),
    )
    return {
        "parity": not entity_differences and not relation_differences and not canonical_differences,
        "leftHirDigest": left_hir.digest(), "rightHirDigest": right_hir.digest(),
        "entityDifferences": entity_differences,
        "relationDifferences": relation_differences,
        "canonicalSemanticDifferences": canonical_differences,
    }


_MISSING = object()
