#!/usr/bin/env python3
"""Run the private evaluator without importing candidate code in this process."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evaluator_boundary import hash_tree, safe_workspace_file, sha256_bytes, sha256_file


EVALUATOR_ID = "EVAL-RELEASE-NOTES-EXTERNAL"
EVALUATOR_ROOT = Path(__file__).resolve().parent


def is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def private_input_paths() -> list[Path]:
    return [
        path
        for path in sorted(EVALUATOR_ROOT.rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    ]


def private_hashes() -> dict[str, str]:
    return {
        path.relative_to(EVALUATOR_ROOT).as_posix(): sha256_file(path)
        for path in private_input_paths()
    }


def file_digest(workspace: Path, relative: str) -> str | None:
    path, _error = safe_workspace_file(workspace, relative)
    return sha256_file(path) if path is not None else None


def capture_git(workspace: Path, arguments: list[str]) -> subprocess.CompletedProcess[bytes]:
    env = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "HOME": "/nonexistent",
        "LANG": "C",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }
    return subprocess.run(
        [
            "git",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.hooksPath=/dev/null",
            *arguments,
        ],
        cwd=workspace,
        env=env,
        capture_output=True,
        check=False,
    )


def git_binding(workspace: Path) -> dict[str, Any]:
    head_result = capture_git(workspace, ["rev-parse", "--verify", "HEAD"])
    if head_result.returncode != 0:
        return {
            "available": False,
            "error": "workspace has no readable Git HEAD",
            "headCommit": None,
            "trackedDiffSha256": None,
            "statusSha256": None,
            "baselineManifestSha256": None,
        }
    head = head_result.stdout.decode("ascii", errors="replace").strip()
    diff = capture_git(
        workspace,
        ["diff", "--binary", "--no-ext-diff", head, "--"],
    )
    status = capture_git(
        workspace,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
    )
    baseline_manifest = capture_git(workspace, ["show", f"{head}:.hdp/manifest.json"])
    available = diff.returncode == 0 and status.returncode == 0
    return {
        "available": available,
        "error": None if available else "Git diff or status could not be read",
        "headCommit": head,
        "trackedDiffSha256": sha256_bytes(diff.stdout) if diff.returncode == 0 else None,
        "trackedDiffBytes": len(diff.stdout) if diff.returncode == 0 else None,
        "statusSha256": sha256_bytes(status.stdout) if status.returncode == 0 else None,
        "statusBytes": len(status.stdout) if status.returncode == 0 else None,
        "baselineManifestSha256": (
            sha256_bytes(baseline_manifest.stdout)
            if baseline_manifest.returncode == 0
            else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    fixture = args.fixture.resolve()
    evidence = args.evidence.resolve()

    if not fixture.is_dir():
        parser.error(f"fixture is not a directory: {fixture}")
    if is_within(evidence, fixture) or is_within(fixture, evidence):
        parser.error("evidence and fixture paths must not overlap")
    if is_within(fixture, EVALUATOR_ROOT) or is_within(EVALUATOR_ROOT, fixture):
        parser.error("fixture and private evaluator paths must not overlap")
    if is_within(evidence, EVALUATOR_ROOT) or is_within(EVALUATOR_ROOT, evidence):
        parser.error("evidence and private evaluator paths must not overlap")

    evidence.mkdir(parents=True, exist_ok=True)
    test_file = EVALUATOR_ROOT / "test_acceptance.py"
    contract = EVALUATOR_ROOT / "private_contract.json"
    control_proof_path = evidence / "control-proof.json"

    private_before = private_hashes()
    workspace_tree_before, _snapshot_before = hash_tree(fixture)
    git_before = git_binding(fixture)
    manifest_before = file_digest(fixture, ".hdp/manifest.json")
    ledger_before = file_digest(fixture, "evidence/ledger.jsonl")

    command = [
        sys.executable,
        str(test_file),
        str(fixture),
        "--result-json",
        str(control_proof_path),
    ]
    evaluator_env = os.environ.copy()
    evaluator_env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        result = subprocess.run(
            command,
            cwd=EVALUATOR_ROOT,
            env=evaluator_env,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = (
            exc.stdout.decode("utf-8", errors="replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        stderr = (
            exc.stderr.decode("utf-8", errors="replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
        timed_out = True

    stdout_path = evidence / "evaluator.stdout.log"
    stderr_path = evidence / "evaluator.stderr.log"
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")

    private_after = private_hashes()
    workspace_tree_after, _snapshot_after = hash_tree(fixture)
    git_after = git_binding(fixture)
    manifest_after = file_digest(fixture, ".hdp/manifest.json")
    ledger_after = file_digest(fixture, "evidence/ledger.jsonl")

    control_proof: dict[str, Any] = {}
    control_proof_error: str | None = None
    if control_proof_path.is_file():
        try:
            loaded = json.loads(control_proof_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                control_proof = loaded
            else:
                control_proof_error = "control proof is not a JSON object"
        except json.JSONDecodeError:
            control_proof_error = "control proof is not valid JSON"
    else:
        control_proof_error = "control proof was not produced"

    private_unchanged = private_before == private_after
    workspace_unchanged = (
        workspace_tree_before == workspace_tree_after
        and git_before == git_after
        and manifest_before == manifest_after
        and ledger_before == ledger_after
    )
    baseline_manifest_matches = (
        manifest_before is not None
        and manifest_before == git_before.get("baselineManifestSha256")
    )
    control_passed = (
        control_proof.get("passed") is True
        and control_proof.get("externalControlProbes", {}).get("passed") is True
    )
    passed = (
        exit_code == 0
        and not timed_out
        and private_unchanged
        and workspace_unchanged
        and git_before.get("available") is True
        and baseline_manifest_matches
        and control_passed
        and control_proof_error is None
    )

    report = {
        "schemaVersion": "2",
        "evaluatorId": EVALUATOR_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "exitCode": exit_code,
        "timedOut": timed_out,
        "passed": passed,
        "fixture": str(fixture),
        "privateInputs": {
            # Retained for report consumers of schema version 1.
            "contractSha256": private_before.get(contract.name),
            "testsSha256": private_before.get(test_file.name),
            "before": private_before,
            "after": private_after,
            "unchanged": private_unchanged,
        },
        "workspaceBinding": {
            "treeSha256Before": workspace_tree_before,
            "treeSha256After": workspace_tree_after,
            "immutableDuringEvaluation": workspace_unchanged,
            "harnessManifest": {
                "path": ".hdp/manifest.json",
                "sha256Before": manifest_before,
                "sha256After": manifest_after,
                "matchesBaselineCommit": baseline_manifest_matches,
            },
            "ledger": {
                "path": "evidence/ledger.jsonl",
                "sha256Before": ledger_before,
                "sha256After": ledger_after,
            },
            "gitBefore": git_before,
            "gitAfter": git_after,
        },
        "externalControl": {
            "sandbox": control_proof.get("sandbox"),
            "probes": control_proof.get("externalControlProbes"),
            "candidateOwnedHarnessIsControlAuthority": False,
        },
        "candidateEvidence": control_proof.get("candidateEvidence"),
        "controlProof": {
            "path": control_proof_path.name,
            "sha256": sha256_file(control_proof_path) if control_proof_path.is_file() else None,
            "error": control_proof_error,
        },
        "logs": ["evaluator.stdout.log", "evaluator.stderr.log"],
        "logDigests": [
            {"path": stdout_path.name, "sha256": sha256_file(stdout_path)},
            {"path": stderr_path.name, "sha256": sha256_file(stderr_path)},
        ],
    }
    report_path = evidence / "evaluation-report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    sys.stdout.write(stdout)
    sys.stderr.write(stderr)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if passed else (exit_code or 1)


if __name__ == "__main__":
    raise SystemExit(main())
