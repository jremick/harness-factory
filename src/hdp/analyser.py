"""Evidence-aware reconstruction of an existing AI harness."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import yaml

from .diagnostics import HdpInputError
from .io import atomic_write_text, dump_json, dump_yaml, load_document
from .schema_validation import load_canonical_schema, structural_diagnostics
from .semantic_validation import semantic_diagnostics


MAX_INVENTORY_FILE_BYTES = 2 * 1024 * 1024
SKIP_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prepare_directory(path: Path, *, label: str, must_exist: bool) -> Path:
    lexical = path.expanduser().absolute()
    if lexical.is_symlink():
        raise HdpInputError(f"{label} path cannot be a symlink: {lexical}")
    resolved = lexical.resolve()
    if must_exist and not resolved.is_dir():
        raise ValueError(f"{label} path is not a directory: {resolved}")
    return resolved


def _regular_tree_files(root: Path, *, skip_parts: set[str]) -> list[Path]:
    """Inventory regular in-root files without following links."""

    files: list[Path] = []
    stack = [root]
    while stack:
        directory = stack.pop()
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as exc:
            raise HdpInputError(f"cannot inspect harness tree {directory}: {exc}") from exc
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(root)
            if entry.is_symlink():
                raise HdpInputError(
                    f"harness analysis rejects symlink: {relative.as_posix()}"
                )
            if any(part in skip_parts for part in relative.parts):
                continue
            if entry.is_dir(follow_symlinks=False):
                stack.append(path)
                continue
            if not entry.is_file(follow_symlinks=False):
                raise HdpInputError(
                    f"harness analysis rejects non-regular file: {relative.as_posix()}"
                )
            resolved = path.resolve()
            if resolved != root and root not in resolved.parents:
                raise HdpInputError(
                    f"harness file resolves outside analysis root: {relative.as_posix()}"
                )
            files.append(path)
    return sorted(files)


def _category(relative: str) -> str:
    name = relative.lower()
    if name.endswith(("agents.md", "agents.override.md")) or "prompt" in name:
        return "prompt-or-instructions"
    if "/skills/" in f"/{name}" or name.endswith("skill.md"):
        return "skill"
    if name.endswith(("config.toml", ".yaml", ".yml", ".json")):
        return "configuration"
    if "/hooks/" in f"/{name}" or "hook" in name:
        return "hook-or-middleware"
    if "/tests/" in f"/{name}" or name.startswith("test") or "/eval" in f"/{name}":
        return "test-or-evaluator"
    if name.startswith(".github/") or "/ci/" in f"/{name}":
        return "ci"
    if name.endswith((".py", ".js", ".ts", ".sh")):
        return "controller-or-script"
    return "documentation-or-artifact"


def inventory_harness(root: Path) -> list[dict[str, Any]]:
    root = _prepare_directory(root, label="harness", must_exist=True)
    records: list[dict[str, Any]] = []
    for path in _regular_tree_files(root, skip_parts=SKIP_PARTS):
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        records.append({
            "path": relative,
            "category": _category(relative),
            "size": size,
            "sha256": _sha256(path),
            "inspection": "included" if size <= MAX_INVENTORY_FILE_BYTES else "digest-only-size-limit",
        })
    return records


def _escape(value: object) -> str:
    return str(value).replace("~", "~0").replace("/", "~1")


def _leaves(value: Any, pointer: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        for key in sorted(value):
            yield from _leaves(value[key], f"{pointer}/{_escape(key)}")
    elif isinstance(value, list):
        if not value:
            yield pointer, []
        for index, item in enumerate(value):
            yield from _leaves(item, f"{pointer}/{index}")
    else:
        yield pointer or "", value


def _evidence_record(
    field: str,
    value: Any,
    *,
    path: str | None,
    digest: str | None,
    status: str,
    confidence: float,
    claim_class: str,
    missing: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "field": field,
        "value": value,
        "claimClass": claim_class,
        "epistemicStatus": status,
        "confidence": confidence,
        "sources": [] if path is None else [{
            "path": path,
            "location": field or "/",
            "digest": f"sha256:{digest}",
            "authority": "generated-source-definition" if status == "declared" else "inspected-runtime-object",
        }],
        "contradictions": [],
        "missingEvidence": missing or [],
        "humanConfirmation": {
            "required": status in {"inferred", "unknown"},
            "reason": "Required normative value lacks sufficient source evidence." if status == "unknown" else "",
        },
    }


def _partial_draft(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    title = root.name or "analysed-harness"
    draft = {
        "hdpVersion": "0.1.0",
        "kind": "HarnessDefinition",
        "metadata": {
            "id": f"urn:hdp:analysis:{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') or 'harness'}",
            "name": re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "harness",
            "title": f"Draft reconstruction of {title}",
            "version": "0.0.0",
            "status": "draft",
        },
    }
    records = [
        _evidence_record(pointer, value, path=None, digest=None, status="inferred", confidence=0.5,
                         claim_class="administrative-metadata")
        for pointer, value in _leaves(draft)
    ]
    required = load_canonical_schema()["required"]
    for key in required:
        if key not in draft:
            records.append(_evidence_record(
                f"/{_escape(key)}", None, path=None, digest=None, status="unknown", confidence=0.0,
                claim_class="absent-or-unknowable",
                missing=[f"An authoritative source declaring required HDP field {key!r}."],
            ))
    return draft, records


def _extract_binding(root: Path) -> dict[str, Any]:
    config_path = root / ".codex" / "config.toml"
    parsed: dict[str, Any] = {}
    if config_path.is_file():
        try:
            parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            parsed = {}
    if parsed.get("mcp_servers"):
        raise HdpInputError(
            "Codex adapter 0.1.0 cannot reconstruct MCP configuration without an exact "
            "canonical capability, policy, and network binding"
        )
    runtime_policy: dict[str, Any] = {}
    runtime_policy_path = root / ".hdp" / "runtime-policy.json"
    if runtime_policy_path.is_file():
        try:
            runtime_policy = json.loads(runtime_policy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            runtime_policy = {}
    return {
        "bindingVersion": "0.1.0",
        "kind": "TargetBinding",
        "target": "codex",
        "adapterVersion": "0.1.0",
        "settings": {
            "model": parsed.get("model") if isinstance(parsed.get("model"), str) else "UNKNOWN-REQUIRED",
            "reasoningEffort": parsed.get("model_reasoning_effort") if parsed.get("model_reasoning_effort") in {"low", "medium", "high", "xhigh"} else "UNKNOWN-REQUIRED",
            "approvalPolicy": parsed.get("approval_policy") if parsed.get("approval_policy") in {"untrusted", "on-request", "never"} else "UNKNOWN-REQUIRED",
            "sandboxMode": parsed.get("sandbox_mode") if parsed.get("sandbox_mode") in {"read-only", "workspace-write", "danger-full-access"} else "UNKNOWN-REQUIRED",
        },
        "externallyEnforcedResources": runtime_policy.get("externallyEnforcedResources", []),
        "commandBindings": runtime_policy.get("commandBindings", {}),
        "mcpServers": [],
    }


def _harness_card(draft: dict[str, Any], coverage: dict[str, Any]) -> str:
    title = draft.get("metadata", {}).get("title", "Unresolved harness")
    return f"""# HarnessCard

Subject: {title}  
Reconstruction status: `{coverage['reconstructionStatus']}`  
Evidence coverage: `{coverage['evidencedRequiredFamilies']}/{coverage['requiredFamilies']}`  
Unknown required families: `{coverage['unknownRequiredFamilies']}`

This card describes inspected evidence. It does not assert unobserved runtime
behaviour, target fitness, sandbox enforcement, or release eligibility.
"""


def _hidden_projection_unknowns(draft: dict[str, Any]) -> list[tuple[str, str]]:
    required_fields = {
        "datasets": ("id", "name", "visibility", "version", "custodian"),
        "fixtures": ("id", "name", "visibility", "custodian", "commitment"),
        "tests": (
            "id", "name", "type", "visibility", "evaluatorId", "scenarioIds",
            "requirementIds", "expected", "evidenceArtifactId",
        ),
    }
    unknowns: list[tuple[str, str]] = []
    evaluation = draft.get("evaluation", {})
    for collection, fields in required_fields.items():
        for index, item in enumerate(evaluation.get(collection, [])):
            if item.get("visibility") != "hidden":
                continue
            for field in fields:
                if field not in item:
                    unknowns.append(
                        (f"/evaluation/{collection}/{index}/{_escape(field)}", field)
                    )
    return unknowns


def analyse_harness(harness: Path, output: Path, *, allow_partial: bool = False) -> dict[str, Any]:
    root = _prepare_directory(harness, label="harness", must_exist=True)
    inventory = inventory_harness(root)
    output = _prepare_directory(output, label="analysis output", must_exist=False)
    if output == root or root in output.parents:
        raise HdpInputError("analysis output must be outside the inspected harness root")
    if output.exists():
        _regular_tree_files(output, skip_parts=set())
    output.mkdir(parents=True, exist_ok=True)
    source_path = root / ".hdp" / "source-definition.public.json"
    evidence: list[dict[str, Any]]
    if source_path.is_file():
        draft = load_document(source_path)
        digest = _sha256(source_path)
        evidence = [
            _evidence_record(
                pointer, value, path=source_path.relative_to(root).as_posix(), digest=digest,
                status="declared", confidence=0.99,
                claim_class=("evidenced-intended-outcome" if pointer.startswith("/purpose") else "operational-behavior"),
            )
            for pointer, value in _leaves(draft)
        ]
        projection_unknowns = _hidden_projection_unknowns(draft)
        evidence.extend(
            _evidence_record(
                pointer, None, path=None, digest=None, status="unknown", confidence=0.0,
                claim_class="absent-or-unknowable",
                missing=[
                    f"The public projection intentionally omits hidden evaluator field {field!r}."
                ],
            )
            for pointer, field in projection_unknowns
        )
        projected = bool(projection_unknowns)
        reconstruction_extension = {
            "evidenceMap": "evidence-map.json",
            "generationReady": not projected,
            "sourceMode": (
                "embedded-generated-public-projection" if projected
                else "embedded-generated-source-definition"
            ),
        }
        draft.setdefault("extensions", {})["x-hdp-reconstruction"] = reconstruction_extension
        source_mode = reconstruction_extension["sourceMode"]
    else:
        if not allow_partial:
            raise HdpInputError(
                "arbitrary harness reconstruction requires evidence-aware skill/model reasoning; "
                "use the analyse CLI or Agent Skill to produce an explicit partial draft"
            )
        draft, evidence = _partial_draft(root)
        source_mode = "evidence-limited-partial-draft"

    structural = structural_diagnostics(draft)
    semantic = [] if structural else semantic_diagnostics(draft, root)
    required = load_canonical_schema()["required"]
    unknown_families = sorted(key for key in required if key not in draft)
    coverage = {
        "reconstructionStatus": (
            "implementation-aligned-draft" if source_mode.startswith("embedded") and not structural and not semantic
            else "incomplete-reconstruction"
        ),
        "sourceMode": source_mode,
        "requiredFamilies": len(required),
        "evidencedRequiredFamilies": len(required) - len(unknown_families),
        "unknownRequiredFamilies": unknown_families,
        "inventoryFiles": len(inventory),
        "evidenceRecords": len(evidence),
        "structuralStatus": "pass" if not structural else "fail",
        "semanticStatus": "pass" if not semantic and not structural else "not-run" if structural else "fail",
        "structuralDiagnostics": [item.to_dict() for item in structural],
        "semanticDiagnostics": [item.to_dict() for item in semantic],
    }
    uncertainty = {
        "unknowns": [item for item in evidence if item["epistemicStatus"] == "unknown"],
        "inferences": [item for item in evidence if item["epistemicStatus"] == "inferred"],
        "conflicts": [item for item in evidence if item["contradictions"]],
        "releaseBlocking": bool(unknown_families or structural or semantic),
    }
    parity_suite = {
        "version": "0.1.0",
        "semantic": {
            "exact": ["capabilities", "permissions", "approvals", "actors", "states", "transitions", "artifacts", "evaluators"],
            "unsupportedPopulatedFactsMaximum": 0,
        },
        "structural": {"inventoryPaths": [item["path"] for item in inventory]},
        "behavioural": {
            "requiredScenarios": ["feature", "defect-fix", "constrained-refactor", "policy-block"],
            "requiredParity": 1.0,
            "status": "not-run",
        },
    }
    source_inventory = {
        "root": ".",
        "inspectedAt": datetime.now(timezone.utc).isoformat(),
        "files": inventory,
        "excluded": sorted(SKIP_PARTS),
    }
    atomic_write_text(output / "draft-hdp.yaml", dump_yaml(draft))
    atomic_write_text(output / "hdp.reconstructed.yaml", dump_yaml(draft))
    atomic_write_text(output / "evidence-map.json", dump_json({"version": "0.1.0", "records": evidence}))
    atomic_write_text(output / "source-inventory.json", dump_json(source_inventory))
    atomic_write_text(output / "coverage-report.json", dump_json(coverage))
    atomic_write_text(output / "uncertainty-report.json", dump_json(uncertainty))
    atomic_write_text(output / "parity-suite.json", dump_json(parity_suite))
    atomic_write_text(output / "codex-binding.yaml", dump_yaml(_extract_binding(root)))
    atomic_write_text(output / "HarnessCard.md", _harness_card(draft, coverage))
    return {
        "output": str(output), "sourceMode": source_mode,
        "valid": not structural and not semantic,
        "fieldAssessmentCount": len(evidence),
        "structuralStatus": coverage["structuralStatus"],
        "semanticStatus": coverage["semanticStatus"],
        "unknownRequiredFamilies": unknown_families,
        "inventoryFiles": len(inventory), "evidenceRecords": len(evidence),
    }
