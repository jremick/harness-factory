#!/usr/bin/env python3
"""Build and self-check the content-addressed release-evidence bundle."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from hdp.bindings import load_codex_binding
from hdp.compiler import validate_and_normalise
from hdp.conformance import binding_digest, stable_binding_identity, subject_bindings
from hdp.io import dump_json
from hdp.packaging import _tree_digest
from hdp.verification_evidence import validate_verification_bundle


TASKS = ("feature", "defect-fix", "refactor", "policy-block")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(path: Path, root: Path) -> str:
    resolved = path.resolve()
    root = root.resolve()
    if path.is_symlink() or not path.is_file() or root not in resolved.parents:
        raise ValueError(f"evidence must be a regular file below {root}: {path}")
    return resolved.relative_to(root).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--harness", type=Path, required=True)
    parser.add_argument("--definition", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--local-verification", type=Path, required=True)
    parser.add_argument("--analyser-coverage", type=Path, required=True)
    parser.add_argument("--sandbox-probe", type=Path, required=True)
    parser.add_argument("--independent-review", type=Path, required=True)
    parser.add_argument(
        "--behaviour",
        action="append",
        default=[],
        metavar="TASK=PATH",
        help="Exactly one aggregate JSON for each reference task.",
    )
    parser.add_argument("--retained-failure", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    evidence_root = args.evidence_root.resolve()
    output = args.output.resolve()
    if output.exists():
        raise ValueError(f"output already exists: {output}")
    if output.parent != evidence_root:
        raise ValueError("bundle output must be directly below --evidence-root")

    behaviour: dict[str, Path] = {}
    for value in args.behaviour:
        task, separator, raw_path = value.partition("=")
        if not separator or task not in TASKS or task in behaviour:
            raise ValueError(f"invalid or duplicate --behaviour value: {value!r}")
        behaviour[task] = Path(raw_path)
    if set(behaviour) != set(TASKS):
        raise ValueError(f"behaviour evidence must cover exactly: {', '.join(TASKS)}")

    binding = load_codex_binding(args.binding)
    hir = validate_and_normalise(
        args.definition,
        binding_ref=stable_binding_identity(binding),
    )
    subjects = subject_bindings(
        definition_id=hir.source_id,
        definition_digest=hir.source_digest,
        hir_digest=hir.digest(),
        binding_target=binding.target,
        binding_digest_value=binding_digest(binding),
        harness_digest=_tree_digest(args.harness.resolve(), ignore_ephemeral=True),
    )
    sources = {
        "local-verification": args.local_verification,
        "analyser-coverage": args.analyser_coverage,
        "sandbox-probe": args.sandbox_probe,
        "independent-review": args.independent_review,
        **{f"behaviour-{task}": path for task, path in behaviour.items()},
    }
    artifacts = []
    for artifact_id, path in sorted(sources.items()):
        relative = inside(path, evidence_root)
        artifacts.append({"id": artifact_id, "path": relative, "sha256": sha256(path)})
    retained = [
        {"path": inside(Path(path), evidence_root), "sha256": sha256(Path(path))}
        for path in args.retained_failure
    ]
    value = {
        "schemaVersion": "0.1.0",
        "kind": "FactoryVerificationEvidence",
        "subject": subjects,
        "artifacts": artifacts,
        "retainedFailures": retained,
    }
    output.write_text(dump_json(value), encoding="utf-8")
    conformance, _paths = validate_verification_bundle(output, subjects)
    print(dump_json({
        "status": conformance["status"],
        "releaseEligible": conformance["releaseEligible"],
        "subject": subjects,
        "bundle": str(output),
        "bundleSha256": sha256(output),
    }), end="")
    return 0 if conformance["releaseEligible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
