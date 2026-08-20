"""Deterministic local release packaging and tamper verification."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
import stat
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .adapters import CodexAdapter
from . import __version__
from .bindings import CodexBinding, load_codex_binding
from .compiler import validate_and_normalise
from .conformance import (
    binding_digest,
    binding_document,
    canonicalise_conformance,
    declares_comparative_attribution,
    empty_conformance,
    stable_binding_identity,
    subject_bindings,
)
from .diagnostics import HdpGenerationError
from .hir import HIR
from .io import atomic_write_text, canonical_json, dump_json
from .normalise import normalise_hdp
from .verification_evidence import validate_verification_bundle


_IGNORED_TREE_PARTS = frozenset({"__pycache__", ".pytest_cache", ".git"})
_STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
_BUILD_PREDICATE_TYPE = "https://harnessfactory.dev/attestation/build/v0.1"
_CONFORMANCE_PREDICATE_TYPE = "https://harnessfactory.dev/attestation/conformance/v0.1"
_MAX_RELEASE_FILE_BYTES = 16 * 1024 * 1024
_MAX_JSON_BYTES = 8 * 1024 * 1024
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
_READ_FLAGS = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _included(relative: Path) -> bool:
    return not any(part in _IGNORED_TREE_PARTS for part in relative.parts)


def _read_descriptor(descriptor: int, label: str, *, maximum: int) -> bytes:
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        raise HdpGenerationError(f"{label} must be a regular file")
    if metadata.st_size > maximum:
        raise HdpGenerationError(f"{label} exceeds the {maximum}-byte limit")
    chunks: list[bytes] = []
    remaining = maximum + 1
    while remaining:
        chunk = os.read(descriptor, min(1024 * 1024, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    content = b"".join(chunks)
    if len(content) > maximum or len(content) != metadata.st_size:
        raise HdpGenerationError(f"{label} changed or exceeded its size limit while read")
    return content


def _read_regular_bytes(path: Path, label: str, *, maximum: int) -> bytes:
    try:
        descriptor = os.open(path, _READ_FLAGS)
    except OSError as exc:
        raise HdpGenerationError(f"{label} is missing or unsafe: {exc}") from exc
    try:
        return _read_descriptor(descriptor, label, maximum=maximum)
    finally:
        os.close(descriptor)


def _read_regular_beneath(
    root: Path, relative: str, label: str, *, maximum: int
) -> bytes:
    safe = _safe_relative(relative)
    if safe is None:
        raise HdpGenerationError(f"{label} has an unsafe path")
    relative_path = PurePosixPath(safe)
    root_fd = os.open(root, _DIRECTORY_FLAGS)
    parent_fd = os.dup(root_fd)
    descriptor: int | None = None
    try:
        for part in relative_path.parent.parts:
            if part == ".":
                continue
            next_fd = os.open(part, _DIRECTORY_FLAGS, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        descriptor = os.open(relative_path.name, _READ_FLAGS, dir_fd=parent_fd)
        return _read_descriptor(descriptor, label, maximum=maximum)
    except OSError as exc:
        raise HdpGenerationError(f"{label} is missing or unsafe: {exc}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_fd)
        os.close(root_fd)


def _read_json_beneath(root: Path, relative: str, label: str) -> Any:
    try:
        content = _read_regular_beneath(root, relative, label, maximum=_MAX_JSON_BYTES)
        return json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HdpGenerationError(f"{label} does not match valid JSON: {exc}") from exc


def _audit_regular_tree(root: Path, *, label: str) -> None:
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if not _included(relative):
            continue
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise HdpGenerationError(f"{label} cannot contain symlink: {relative}")
        if not (stat.S_ISREG(metadata.st_mode) or stat.S_ISDIR(metadata.st_mode)):
            raise HdpGenerationError(
                f"{label} cannot contain non-regular entry: {relative}"
            )


def _copy_regular_tree(source: Path, target: Path) -> None:
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if not _included(relative):
            continue
        destination = target / relative
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise HdpGenerationError(f"release payload cannot contain symlink: {relative}")
        if stat.S_ISDIR(metadata.st_mode):
            destination.mkdir(parents=True, exist_ok=True)
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise HdpGenerationError(
                f"release payload cannot contain non-regular entry: {relative}"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(
            _read_regular_beneath(
                source,
                relative.as_posix(),
                f"release payload source {relative}",
                maximum=_MAX_RELEASE_FILE_BYTES,
            )
        )
        os.chmod(destination, stat.S_IMODE(metadata.st_mode))


def _entries(root: Path, *, ignore_ephemeral: bool = False) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        relative_path = path.relative_to(root)
        if ignore_ephemeral and not _included(relative_path):
            continue
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise HdpGenerationError(f"release payload cannot contain symlink: {relative_path}")
        if stat.S_ISDIR(metadata.st_mode):
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise HdpGenerationError(
                f"release payload cannot contain non-regular entry: {relative_path}"
            )
        relative = relative_path.as_posix()
        content = _read_regular_beneath(
            root,
            relative,
            f"release payload file {relative}",
            maximum=_MAX_RELEASE_FILE_BYTES,
        )
        mode = stat.S_IMODE(metadata.st_mode)
        records.append({
            "path": relative,
            "sha256": _sha256_bytes(content),
            "size": len(content),
            "executable": bool(mode & 0o111),
            "mediaType": mimetypes.guess_type(relative)[0] or "application/octet-stream",
        })
    return records


def _tree_digest(root: Path, *, ignore_ephemeral: bool = False) -> str:
    return _sha256_bytes(canonical_json(_entries(root, ignore_ephemeral=ignore_ephemeral)).encode())


def _read_json(path: Path, label: str) -> Any:
    try:
        content = _read_regular_bytes(path, label, maximum=_MAX_JSON_BYTES)
        return json.loads(content.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HdpGenerationError(f"{label} does not match valid JSON: {exc}") from exc


def _safe_relative(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value != path.as_posix():
        return None
    return value


def _validate_generated_harness(
    harness: Path, hir: HIR, binding: CodexBinding
) -> None:
    """Reject a stale/mismatched compile and modified or untracked controls."""

    _audit_regular_tree(harness, label="generated harness")
    manifest = _read_json_beneath(
        harness, ".hdp/manifest.json", "generated harness manifest"
    )
    if not isinstance(manifest, dict):
        raise HdpGenerationError("generated harness manifest must be an object")
    source = manifest.get("source")
    semantics = hir.canonical_semantics
    expected_source = {
        "id": hir.source_id,
        "version": semantics.get("metadata", {}).get("version"),
        "sha256": hir.source_digest,
    }
    if source != expected_source:
        raise HdpGenerationError("generated harness does not match the supplied definition")

    embedded_hir = _read_json_beneath(
        harness, ".hdp/hir.json", "generated harness HIR"
    )
    if embedded_hir != CodexAdapter._public_hir(hir):
        raise HdpGenerationError("generated harness does not match the supplied definition or binding")
    plan = _read_json_beneath(
        harness, ".hdp/compile-plan.json", "generated harness compile plan"
    )
    if not isinstance(plan, dict) or (
        plan.get("adapter") != "codex"
        or plan.get("hir_digest") != hir.digest()
        or plan.get("adapter_version") != "0.1.0"
    ):
        raise HdpGenerationError("generated harness compile plan does not match its HIR and binding")

    adapter = CodexAdapter(binding)
    compile_plan = adapter.plan(hir)
    expected_files, expected_source_map = adapter._expected_files(hir, compile_plan)
    expected_manifest = {
        "manifestVersion": "1",
        "generator": {"name": "harness-factory", "version": __version__},
        "source": expected_source,
        "artifacts": [
            {
                "path": relative,
                "sha256": _sha256_bytes(content.encode("utf-8")),
                "sourceFields": expected_source_map.get(relative, []),
            }
            for relative, content in sorted(expected_files.items())
        ],
        "staleGeneratedArtifactsRetained": [],
        "manualExtensionRoot": "manual/",
    }
    if manifest != expected_manifest:
        raise HdpGenerationError("generated harness manifest was modified or is not canonical")
    for relative, content in expected_files.items():
        actual = _read_regular_beneath(
            harness, relative, f"generated artifact {relative}", maximum=_MAX_RELEASE_FILE_BYTES
        )
        if _sha256_bytes(actual) != _sha256_bytes(content.encode("utf-8")):
            raise HdpGenerationError(f"generated artifact was modified: {relative}")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise HdpGenerationError("generated harness manifest artifacts must be an array")
    tracked_paths: set[str] = set()
    for record in artifacts:
        if not isinstance(record, dict) or set(record) != {"path", "sha256", "sourceFields"}:
            raise HdpGenerationError("generated harness artifact record is invalid")
        relative = _safe_relative(record.get("path"))
        if relative is None or relative in tracked_paths:
            raise HdpGenerationError("generated harness artifact path is unsafe or duplicated")
        tracked_paths.add(relative)
        actual = _read_regular_beneath(
            harness, relative, f"generated artifact {relative}", maximum=_MAX_RELEASE_FILE_BYTES
        )
        if _sha256_bytes(actual) != record.get("sha256"):
            raise HdpGenerationError(f"generated artifact was modified: {relative}")

    actual_paths: set[str] = set()
    for path in sorted(harness.rglob("*")):
        relative_path = path.relative_to(harness)
        if not _included(relative_path):
            continue
        relative = relative_path.as_posix()
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise HdpGenerationError(f"generated harness cannot contain symlink: {relative}")
        if stat.S_ISDIR(metadata.st_mode):
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise HdpGenerationError(
                f"generated harness cannot contain non-regular entry: {relative}"
            )
        if stat.S_ISREG(metadata.st_mode):
            actual_paths.add(relative)
    actual_paths.discard(".hdp/manifest.json")
    untracked = sorted(actual_paths - tracked_paths)
    if untracked:
        raise HdpGenerationError(
            "generated harness contains untracked files; package only the exact "
            "manifest-owned tree: " + ", ".join(untracked)
        )


def _statement(
    name: str, predicate_type: str, payload_digest: str, predicate: dict[str, Any]
) -> dict[str, Any]:
    return {
        "_type": _STATEMENT_TYPE,
        "subject": [{"name": "payload", "digest": {"sha256": payload_digest}}],
        "predicateType": predicate_type,
        "predicate": {
            "name": name,
            "assurance": "unsigned-digest-only",
            "authenticated": False,
            **predicate,
        },
    }


def _build_statement(
    payload_digest: str, hir: HIR, binding: CodexBinding
) -> dict[str, Any]:
    return _statement(
        "harness-factory-build",
        _BUILD_PREDICATE_TYPE,
        payload_digest,
        {
            "buildType": "https://harnessfactory.dev/build/codex-harness/v0.1",
            "builder": {"id": f"harness-factory/{__version__}"},
            "materials": [
                {"uri": hir.source_id, "digest": {"sha256": hir.source_digest}},
                {
                    "uri": f"target-binding:{binding.target}",
                    "digest": {"sha256": binding_digest(binding)},
                },
            ],
            "hirDigest": hir.digest(),
        },
    )


def _conformance_statement(
    payload_digest: str, conformance: Mapping[str, Any]
) -> dict[str, Any]:
    return _statement(
        "harness-factory-conformance",
        _CONFORMANCE_PREDICATE_TYPE,
        payload_digest,
        {"conformance": dict(conformance)},
    )


def package_release(
    harness: Path,
    definition: Path,
    binding: Path,
    output: Path,
    *,
    conformance: Path | None = None,
) -> dict[str, Any]:
    if harness.is_symlink():
        raise HdpGenerationError(f"generated harness cannot be a symlink: {harness}")
    if output.is_symlink():
        raise HdpGenerationError(f"release output cannot be a symlink: {output}")
    harness = harness.resolve()
    output = output.resolve()
    if not harness.is_dir():
        raise HdpGenerationError(f"generated harness does not exist: {harness}")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise HdpGenerationError(f"release output must be empty: {output}")

    binding_model = load_codex_binding(binding)
    hir = validate_and_normalise(
        definition, binding_ref=stable_binding_identity(binding_model)
    )
    _validate_generated_harness(harness, hir, binding_model)
    harness_digest = _tree_digest(harness, ignore_ephemeral=True)
    subjects = subject_bindings(
        definition_id=hir.source_id,
        definition_digest=hir.source_digest,
        hir_digest=hir.digest(),
        binding_target=binding_model.target,
        binding_digest_value=binding_digest(binding_model),
        harness_digest=harness_digest,
    )
    comparative = declares_comparative_attribution(hir.canonical_semantics)
    evidence_paths: dict[str, Path] = {}
    if conformance is not None:
        if comparative:
            raise HdpGenerationError(
                "verified comparative-attribution evidence is not implemented in v0.1"
            )
        conformance_data, evidence_paths = validate_verification_bundle(
            conformance, subjects
        )
    else:
        conformance_data = empty_conformance(
            subjects, comparative_attribution=comparative
        )

    payload = output / "payload"
    payload.mkdir(parents=True, exist_ok=True)
    _copy_regular_tree(harness, payload / "harness")
    atomic_write_text(payload / "resolved-hir.json", dump_json(hir.canonical_dict()))
    atomic_write_text(payload / "resolved-binding.json", dump_json(binding_document(binding_model)))
    atomic_write_text(payload / "conformance.json", dump_json(conformance_data))
    if conformance is not None:
        evidence_root = payload / "verification-evidence"
        atomic_write_text(evidence_root / "bundle.json", conformance.read_text(encoding="utf-8"))
        for path in evidence_paths.values():
            relative = path.relative_to(conformance.parent.resolve())
            destination = evidence_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
    records = _entries(payload)
    payload_digest = _sha256_bytes(canonical_json(records).encode())
    manifest = {
        "manifestVersion": "0.1.0",
        "digestAlgorithm": "sha256",
        "payloadDigest": payload_digest,
        "files": records,
        "releaseEligible": conformance_data["releaseEligible"],
    }
    atomic_write_text(output / "release-manifest.json", dump_json(manifest))
    attestations = output / "attestations"
    atomic_write_text(
        attestations / "build.intoto.json",
        dump_json(_build_statement(payload_digest, hir, binding_model)),
    )
    atomic_write_text(
        attestations / "tests.intoto.json",
        dump_json(_conformance_statement(payload_digest, conformance_data)),
    )
    return {
        "status": "pass",
        "releaseEligible": manifest["releaseEligible"],
        "payloadDigest": payload_digest,
        "files": len(records),
        "output": str(output),
        "assurance": "unsigned-digest-only",
    }


def _load_release_subjects(
    payload: Path, computed_digest: str, errors: list[str]
) -> tuple[HIR | None, CodexBinding | None, dict[str, Any] | None, bool]:
    hir: HIR | None = None
    binding: CodexBinding | None = None
    conformance: dict[str, Any] | None = None
    eligible = False
    try:
        raw_hir = _read_json(payload / "resolved-hir.json", "resolved HIR")
        hir = HIR.model_validate(raw_hir)
        raw_binding = _read_json(payload / "resolved-binding.json", "resolved binding")
        binding = CodexBinding.model_validate(raw_binding)
        expected_hir = normalise_hdp(
            hir.canonical_semantics,
            binding_ref=stable_binding_identity(binding),
        )
        if hir.canonical_dict() != expected_hir.canonical_dict():
            errors.append("resolved HIR is not the canonical normalization of its definition and binding")
        _validate_generated_harness(payload / "harness", expected_hir, binding)
        subjects = subject_bindings(
            definition_id=expected_hir.source_id,
            definition_digest=expected_hir.source_digest,
            hir_digest=expected_hir.digest(),
            binding_target=binding.target,
            binding_digest_value=binding_digest(binding),
            harness_digest=_tree_digest(payload / "harness"),
        )
        raw_conformance = _read_json(payload / "conformance.json", "conformance record")
        evidence_bundle = payload / "verification-evidence" / "bundle.json"
        if evidence_bundle.is_file():
            if declares_comparative_attribution(expected_hir.canonical_semantics):
                raise HdpGenerationError(
                    "verified comparative-attribution evidence is not implemented in v0.1"
                )
            canonical, _evidence_paths = validate_verification_bundle(
                evidence_bundle, subjects
            )
        else:
            canonical = canonicalise_conformance(
                raw_conformance,
                expected_subject=subjects,
                comparative_attribution_required=declares_comparative_attribution(
                    expected_hir.canonical_semantics
                ),
            )
            if canonical["releaseEligible"]:
                errors.append(
                    "eligible conformance is missing locally recomputable verification evidence"
                )
        if raw_conformance != canonical:
            errors.append("conformance decision fields or gate order are not canonical")
        conformance = canonical
        eligible = canonical["releaseEligible"] is True
    except (HdpGenerationError, ValueError, TypeError, KeyError) as exc:
        errors.append(f"invalid release subject binding: {exc}")
    return hir, binding, conformance, eligible


def verify_release(release: Path) -> dict[str, Any]:
    lexical = release.expanduser().absolute()
    if lexical.is_symlink():
        return {
            "status": "fail", "verified": False, "releaseEligible": False,
            "errors": ["release root cannot be a symlink"],
        }
    release = lexical.resolve()
    if not release.is_dir():
        return {
            "status": "fail", "verified": False, "releaseEligible": False,
            "errors": ["release root must be a directory"],
        }
    for path in sorted(release.rglob("*")):
        relative = path.relative_to(release).as_posix()
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            return {
                "status": "fail", "verified": False, "releaseEligible": False,
                "errors": [f"symlink is not permitted: {relative}"],
            }
        if not (stat.S_ISREG(metadata.st_mode) or stat.S_ISDIR(metadata.st_mode)):
            return {
                "status": "fail", "verified": False, "releaseEligible": False,
                "errors": [f"non-regular release entry is not permitted: {relative}"],
            }
    errors: list[str] = []
    try:
        manifest = _read_json(release / "release-manifest.json", "release manifest")
    except HdpGenerationError as exc:
        return {"status": "fail", "verified": False, "errors": [*errors, str(exc)]}
    if not isinstance(manifest, dict):
        return {"status": "fail", "verified": False, "errors": ["release manifest must be an object"]}
    if set(manifest) != {
        "manifestVersion", "digestAlgorithm", "payloadDigest", "files", "releaseEligible",
    }:
        errors.append("release manifest fields are not the closed v0.1 set")
    if manifest.get("manifestVersion") != "0.1.0":
        errors.append("unsupported release manifest version")
    if manifest.get("digestAlgorithm") != "sha256":
        errors.append("unsupported release digest algorithm")
    if not isinstance(manifest.get("releaseEligible"), bool):
        errors.append("release manifest eligibility must be boolean")
    files = manifest.get("files")
    if not isinstance(files, list):
        errors.append("release manifest files must be an array")
        files = []

    expected: dict[str, dict[str, Any]] = {}
    for item in files:
        if not isinstance(item, dict) or set(item) != {
            "path", "sha256", "size", "executable", "mediaType",
        }:
            errors.append("release manifest contains an invalid file record")
            continue
        relative = _safe_relative(item.get("path"))
        if relative is None or relative in expected:
            errors.append("release manifest contains an unsafe or duplicated path")
            continue
        expected[relative] = item

    payload = release / "payload"
    actual_paths: set[str] = set()
    if not payload.is_dir():
        errors.append("missing payload directory")
    else:
        for path in sorted(payload.rglob("*")):
            relative = path.relative_to(payload).as_posix()
            if path.is_file():
                actual_paths.add(relative)
                record = expected.get(relative)
                if record is None:
                    errors.append(f"unexpected payload file: {relative}")
                    continue
                try:
                    content = _read_regular_bytes(
                        path, f"payload file {relative}", maximum=_MAX_RELEASE_FILE_BYTES
                    )
                except HdpGenerationError as exc:
                    errors.append(str(exc))
                    continue
                if _sha256_bytes(content) != record.get("sha256"):
                    errors.append(f"content digest mismatch: {relative}")
                if len(content) != record.get("size"):
                    errors.append(f"size mismatch: {relative}")
                executable = bool(stat.S_IMODE(path.stat().st_mode) & 0o111)
                if executable != record.get("executable"):
                    errors.append(f"executable mode mismatch: {relative}")
    for missing in sorted(set(expected) - actual_paths):
        errors.append(f"missing payload file: {missing}")
    try:
        records = _entries(payload) if payload.is_dir() else []
    except HdpGenerationError as exc:
        errors.append(str(exc))
        records = []
    computed_digest = _sha256_bytes(canonical_json(records).encode())
    if records != files:
        errors.append("payload metadata does not match release manifest")
    if computed_digest != manifest.get("payloadDigest"):
        errors.append("payload set digest mismatch")

    hir, binding, conformance, derived_eligibility = _load_release_subjects(
        payload, computed_digest, errors
    )
    if manifest.get("releaseEligible") is not derived_eligibility:
        errors.append("release eligibility does not match deterministic conformance gates")

    expected_statements: dict[str, dict[str, Any]] = {}
    if hir is not None and binding is not None:
        expected_statements["build.intoto.json"] = _build_statement(
            computed_digest, hir, binding
        )
    if conformance is not None:
        expected_statements["tests.intoto.json"] = _conformance_statement(
            computed_digest, conformance
        )
    attestation_dir = release / "attestations"
    if not attestation_dir.is_dir():
        errors.append("missing attestations directory")
    else:
        actual_attestations = {
            path.name for path in attestation_dir.iterdir() if path.is_file()
        }
        unexpected = sorted(actual_attestations - {"build.intoto.json", "tests.intoto.json"})
        if unexpected:
            errors.append("unexpected attestation files: " + ", ".join(unexpected))
    for name in ("build.intoto.json", "tests.intoto.json"):
        path = attestation_dir / name
        try:
            statement = _read_json(path, f"attestation {name}")
            expected_statement = expected_statements.get(name)
            if expected_statement is None or statement != expected_statement:
                errors.append(f"invalid attestation subject or predicate metadata: {name}")
        except HdpGenerationError as exc:
            errors.append(str(exc))

    if release.is_dir():
        allowed_root = {"release-manifest.json", "payload", "attestations"}
        unexpected_root = sorted(path.name for path in release.iterdir() if path.name not in allowed_root)
        if unexpected_root:
            errors.append("unexpected release entries: " + ", ".join(unexpected_root))
    verified = not errors
    return {
        "status": "pass" if verified else "fail",
        "verified": verified,
        "releaseEligible": derived_eligibility and verified,
        "payloadDigest": computed_digest,
        "errors": errors,
    }
