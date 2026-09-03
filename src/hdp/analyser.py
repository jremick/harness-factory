"""Evidence-aware reconstruction of an existing AI harness."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import yaml

from .bindings import CodexBinding
from .cli_contract import (
    SUPPORTED_ADAPTER_VERSION,
    SUPPORTED_BINDING_VERSION,
    SUPPORTED_GENERATED_MANIFEST_VERSION,
    SUPPORTED_HDP_VERSION,
    SUPPORTED_HIR_VERSION,
    unsupported_version_message,
)
from .conformance import binding_digest, subject_bindings
from .diagnostics import HdpError, HdpGenerationError, HdpInputError
from .hir import HIR
from .io import atomic_write_text, canonical_json, dump_json, dump_yaml, load_document
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


def _extract_binding(
    root: Path, *, strict: bool = False, allow_legacy_alpha: bool = False
) -> dict[str, Any]:
    config_path = root / ".codex" / "config.toml"
    parsed: dict[str, Any] = {}
    if config_path.is_file():
        try:
            parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            if strict:
                raise HdpInputError(f"Codex binding configuration is malformed: {exc}") from exc
            parsed = {}
    elif strict:
        raise HdpInputError("Codex binding configuration is missing: .codex/config.toml")
    if parsed.get("mcp_servers"):
        raise HdpInputError(
            "Codex adapter 0.1.0 cannot reconstruct MCP configuration without an exact "
            "canonical capability, policy, and network binding"
        )
    runtime_policy: dict[str, Any] = {}
    runtime_policy_path = root / ".hdp" / "runtime-policy.json"
    if runtime_policy_path.is_file():
        try:
            runtime_policy = load_document(runtime_policy_path)
        except HdpInputError as exc:
            if strict:
                raise HdpInputError(f"Codex runtime policy is invalid: {exc}") from exc
            runtime_policy = {}
    elif strict:
        raise HdpInputError("Codex runtime policy is missing: .hdp/runtime-policy.json")
    if strict:
        legacy_markers_absent = all(
            field not in runtime_policy for field in ("bindingVersion", "adapterVersion")
        )
        for field, subject, expected in (
            ("bindingVersion", "Codex target binding", SUPPORTED_BINDING_VERSION),
            ("adapterVersion", "Codex adapter", SUPPORTED_ADAPTER_VERSION),
        ):
            actual = runtime_policy.get(field)
            if allow_legacy_alpha and legacy_markers_absent:
                actual = expected
            if actual != expected:
                raise HdpInputError(unsupported_version_message(subject, actual, expected))
    return {
        "bindingVersion": runtime_policy.get(
            "bindingVersion", SUPPORTED_BINDING_VERSION
        ),
        "kind": "TargetBinding",
        "target": "codex",
        "adapterVersion": runtime_policy.get(
            "adapterVersion", SUPPORTED_ADAPTER_VERSION
        ),
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


def _path_present(path: Path) -> bool:
    """Check presence without following a possibly hostile final symlink."""

    try:
        path.lstat()
    except FileNotFoundError:
        return False
    return True


def _validate_installed_ownership(
    root: Path,
    generated_manifest: dict[str, Any],
) -> str:
    """Validate only the exact generated files owned by a live installation."""

    from .packaging import _read_regular_beneath, _tree_digest
    from .project import (
        INSTALL_LOCK,
        INSTALL_MANIFEST,
        INSTALL_TRANSACTION,
        _validated_install_manifest,
        _validate_generated_manifest_shape,
    )

    ownership_path = root / INSTALL_MANIFEST
    if not _path_present(ownership_path):
        raise HdpInputError(
            "installed harness is missing the ownership manifest: "
            f"{INSTALL_MANIFEST.as_posix()}"
        )
    ownership = load_document(ownership_path)
    ownership, _previous_files = _validated_install_manifest(ownership)
    generated_manifest = _validate_generated_manifest_shape(generated_manifest)

    transaction_path = root / INSTALL_TRANSACTION
    if _path_present(transaction_path):
        # Keep an interrupted-install journal opaque.  Normal audit never
        # parses or replays a journal authored by another process.
        raise HdpInputError(
            "an unfinished installation requires explicit manual recovery"
        )
    control_root = root / ".harness-factory"
    allowed_controls = {
        INSTALL_MANIFEST.as_posix(),
        INSTALL_LOCK.as_posix(),
    }
    if control_root.is_dir():
        for path in sorted(control_root.rglob("*")):
            if path.is_dir():
                continue
            relative = path.relative_to(root).as_posix()
            if relative not in allowed_controls:
                raise HdpInputError(
                    f"unexpected installer control file: {relative}"
                )
    lock_path = root / INSTALL_LOCK
    if _path_present(lock_path):
        metadata = lock_path.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise HdpInputError("installed harness lock is not a regular file")

    expected_files = [
        {"path": item["path"], "sha256": item["sha256"]}
        for item in generated_manifest["artifacts"]
    ]
    manifest_bytes = _read_regular_beneath(
        root,
        ".hdp/manifest.json",
        "installed generated harness manifest",
        maximum=8 * 1024 * 1024,
    )
    expected_files.append({
        "path": ".hdp/manifest.json",
        "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    })
    if ownership["sourceDefinition"] != generated_manifest["source"]:
        raise HdpInputError(
            "installation ownership does not match the generated source definition"
        )
    if ownership["sourceGenerator"] != generated_manifest["generator"]:
        raise HdpInputError(
            "installation ownership does not match the generated source generator"
        )
    if ownership["files"] != expected_files:
        raise HdpInputError(
            "installation ownership does not enumerate the exact generated files"
        )
    for item in expected_files:
        try:
            content = _read_regular_beneath(
                root,
                item["path"],
                f"installed generated artifact {item['path']}",
                maximum=16 * 1024 * 1024,
            )
        except HdpGenerationError as exc:
            raise HdpInputError(str(exc)) from exc
        if hashlib.sha256(content).hexdigest() != item["sha256"]:
            raise HdpInputError(
                f"installed generated artifact digest mismatch: {item['path']}"
            )
    from .packaging import _tree_digest

    return _tree_digest(
        root,
        include_paths={item["path"] for item in expected_files},
    )


def _validate_embedded_subject(root: Path) -> dict[str, Any]:
    """Validate all generated subject markers before reporting an audit as valid."""

    install_control_present = any(
        _path_present(root / relative)
        for relative in (
            Path(".harness-factory/install-manifest.json"),
            Path(".harness-factory/install.lock"),
            Path(".harness-factory/install-transaction.json"),
        )
    )
    manifest = load_document(root / ".hdp" / "manifest.json")
    if not isinstance(manifest, dict):
        raise HdpInputError("generated harness manifest must be an object")
    if manifest.get("manifestVersion") != SUPPORTED_GENERATED_MANIFEST_VERSION:
        raise HdpInputError(
            unsupported_version_message(
                "generated harness manifest",
                manifest.get("manifestVersion"),
                SUPPORTED_GENERATED_MANIFEST_VERSION,
            )
        )

    source = load_document(root / ".hdp" / "source-definition.public.json")
    if not isinstance(source, dict):
        raise HdpInputError("source HDP must be an object")
    actual_source_version = source.get("hdpVersion")
    if actual_source_version != SUPPORTED_HDP_VERSION:
        raise HdpInputError(
            unsupported_version_message(
                "source HDP", actual_source_version, SUPPORTED_HDP_VERSION
            )
        )

    raw_hir = load_document(root / ".hdp" / "hir.json")
    if not isinstance(raw_hir, dict):
        raise HdpInputError("embedded HIR must be an object")
    for field, subject, expected in (
        ("hir_version", "embedded HIR", SUPPORTED_HIR_VERSION),
        ("source_hdp_version", "embedded HIR source HDP", SUPPORTED_HDP_VERSION),
    ):
        actual = raw_hir.get(field)
        if actual != expected:
            raise HdpInputError(unsupported_version_message(subject, actual, expected))
    semantics = raw_hir.get("canonical_semantics")
    if not isinstance(semantics, dict):
        raise HdpInputError("embedded HIR canonical_semantics must be an object")
    actual_semantics_version = semantics.get("hdpVersion")
    if actual_semantics_version != SUPPORTED_HDP_VERSION:
        raise HdpInputError(
            unsupported_version_message(
                "embedded HIR canonical semantics HDP",
                actual_semantics_version,
                SUPPORTED_HDP_VERSION,
            )
        )
    try:
        embedded_hir = HIR.model_validate(raw_hir)
    except ValueError as exc:
        raise HdpInputError(f"embedded HIR is invalid: {exc}") from exc

    source_digest = hashlib.sha256(canonical_json(source).encode()).hexdigest()
    if embedded_hir.source_digest != source_digest:
        raise HdpInputError("embedded HIR source digest does not match source HDP")
    source_metadata = source.get("metadata")
    if not isinstance(source_metadata, dict):
        raise HdpInputError("source HDP metadata must be an object")
    if embedded_hir.source_id != source_metadata.get("id"):
        raise HdpInputError("embedded HIR source identity does not match source HDP")
    if embedded_hir.canonical_semantics != source:
        raise HdpInputError("embedded HIR canonical semantics do not match source HDP")

    runtime_policy = load_document(root / ".hdp" / "runtime-policy.json")
    if not isinstance(runtime_policy, dict):
        raise HdpInputError("generated runtime policy must be an object")
    policy_version = runtime_policy.get("policyVersion")
    if policy_version != SUPPORTED_HDP_VERSION:
        raise HdpInputError(
            unsupported_version_message(
                "generated runtime policy HDP", policy_version, SUPPORTED_HDP_VERSION
            )
        )
    legacy_alpha = all(
        field not in runtime_policy for field in ("bindingVersion", "adapterVersion")
    )
    binding = CodexBinding.model_validate(
        _extract_binding(root, strict=True, allow_legacy_alpha=legacy_alpha)
    )

    compile_plan = load_document(root / ".hdp" / "compile-plan.json")
    if not isinstance(compile_plan, dict):
        raise HdpInputError("Codex compile plan must be an object")
    if compile_plan.get("adapter") != "codex":
        actual = compile_plan.get("adapter")
        rendered = "<missing>" if actual is None else repr(actual)
        raise HdpInputError(
            f"unsupported generated adapter {rendered}; beta supports 'codex'. "
            "No automatic migration is provided; update the source explicitly "
            "and rerun validation."
        )
    for field, subject, expected in (
        ("plan_version", "Codex compile plan", SUPPORTED_ADAPTER_VERSION),
        ("adapter_version", "Codex adapter", SUPPORTED_ADAPTER_VERSION),
    ):
        actual = compile_plan.get(field)
        if actual != expected:
            raise HdpInputError(unsupported_version_message(subject, actual, expected))

    # The package verifier owns the complete generated-tree/digest comparison.
    # Reuse it here so an audit cannot turn a stale or altered subject into a
    # valid result by relying only on the reconstructed source document.
    from .packaging import _validate_generated_harness, _tree_digest

    try:
        _validate_generated_harness(
            root,
            embedded_hir,
            binding,
            allow_untracked=install_control_present,
        )
    except HdpGenerationError as exc:
        raise HdpInputError(str(exc)) from exc
    if install_control_present:
        harness_digest = _validate_installed_ownership(
            root,
            manifest,
        )
    else:
        from .packaging import _tree_digest

        harness_digest = _tree_digest(root, ignore_ephemeral=True)
    return subject_bindings(
        definition_id=embedded_hir.source_id,
        definition_digest=embedded_hir.source_digest,
        hir_digest=embedded_hir.digest(),
        binding_target=binding.target,
        binding_digest_value=binding_digest(binding),
        harness_digest=harness_digest,
    )


def analyse_harness(
    harness: Path,
    output: Path,
    *,
    allow_partial: bool = False,
    strict_subject: bool | None = None,
) -> dict[str, Any]:
    root = _prepare_directory(harness, label="harness", must_exist=True)
    if strict_subject is None:
        # The direct generator API can intentionally emit source-only fixtures.
        # Once embedded compile metadata exists, default to the fail-closed
        # product subject contract even for import-level callers.
        strict_subject = (root / ".hdp" / "hir.json").exists()
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
    subject_errors: list[str] = []
    if source_mode.startswith("embedded"):
        if strict_subject:
            try:
                coverage["subject"] = _validate_embedded_subject(root)
            except (OSError, ValueError, HdpError) as exc:
                subject_errors.append(str(exc))
                coverage.pop("subject", None)
        else:
            try:
                manifest = load_document(root / ".hdp/manifest.json")
                embedded_hir = HIR.model_validate(load_document(root / ".hdp/hir.json"))
                binding_model = CodexBinding.model_validate(_extract_binding(root))
                from .packaging import _tree_digest

                coverage["subject"] = subject_bindings(
                    definition_id=embedded_hir.source_id,
                    definition_digest=embedded_hir.source_digest,
                    hir_digest=embedded_hir.digest(),
                    binding_target=binding_model.target,
                    binding_digest_value=binding_digest(binding_model),
                    harness_digest=_tree_digest(root, ignore_ephemeral=True),
                )
                if manifest.get("source") != {
                    "id": embedded_hir.source_id,
                    "version": embedded_hir.canonical_semantics.get("metadata", {}).get("version"),
                    "sha256": embedded_hir.source_digest,
                }:
                    coverage.pop("subject", None)
            except (OSError, ValueError, HdpError):
                coverage.pop("subject", None)
    coverage["subjectStatus"] = "pass" if not subject_errors else "fail"
    coverage["subjectDiagnostics"] = subject_errors
    uncertainty = {
        "unknowns": [item for item in evidence if item["epistemicStatus"] == "unknown"],
        "inferences": [item for item in evidence if item["epistemicStatus"] == "inferred"],
        "conflicts": [item for item in evidence if item["contradictions"]],
        "releaseBlocking": bool(
            unknown_families or structural or semantic or subject_errors
        ),
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
        "valid": not structural and not semantic and not subject_errors,
        "fieldAssessmentCount": len(evidence),
        "structuralStatus": coverage["structuralStatus"],
        "semanticStatus": coverage["semanticStatus"],
        "unknownRequiredFamilies": unknown_families,
        "inventoryFiles": len(inventory), "evidenceRecords": len(evidence),
        "subjectStatus": coverage["subjectStatus"],
        "subjectDiagnostics": subject_errors,
    }
