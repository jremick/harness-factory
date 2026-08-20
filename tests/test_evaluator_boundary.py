from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


EVALUATOR_ROOT = Path(__file__).resolve().parents[1] / "evaluator" / "release_notes"


def load_boundary_module():
    spec = importlib.util.spec_from_file_location(
        "release_notes_evaluator_boundary",
        EVALUATOR_ROOT / "evaluator_boundary.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


boundary_module = load_boundary_module()


def write_candidate(workspace: Path) -> Path:
    source = workspace / "src" / "release_notes.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def build_release_notes(changes):\n"
        "    if not isinstance(changes, list):\n"
        "        raise ValueError('changes must be a list')\n"
        "    return '# Release notes\\n'\n",
        encoding="utf-8",
    )
    return source


def test_candidate_runs_only_inside_read_only_network_denied_sandbox(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    candidate_source = write_candidate(workspace)
    private_file = tmp_path / "private-evaluator.json"
    private_file.write_text('{"canary":"private"}\n', encoding="utf-8")
    parent_file = tmp_path / "parent.txt"
    parent_file.write_text("parent\n", encoding="utf-8")

    boundary = boundary_module.SandboxBoundary(workspace)
    if not boundary.available:
        pytest.skip(boundary.describe()["reason"])

    responses, process = boundary_module.run_candidate_requests(
        boundary,
        [
            {
                "id": "functional",
                "operation": "build_release_notes",
                "argument": {"encoding": "json", "value": []},
            }
        ],
    )
    assert process["exitCode"] == 0
    assert responses["functional"] == {
        "id": "functional",
        "ok": True,
        "value": "# Release notes\n",
        "inputMutated": False,
    }

    probes = boundary_module.run_control_probes(
        boundary,
        workspace_read=candidate_source,
        workspace_write=candidate_source,
        private_path=private_file,
        parent_path=parent_file,
    )
    assert probes["passed"] is True
    assert candidate_source.read_text(encoding="utf-8").startswith("def build_release_notes")
    assert private_file.read_text(encoding="utf-8") == '{"canary":"private"}\n'


def test_sandbox_unavailability_is_explicit_and_fail_closed(tmp_path: Path) -> None:
    boundary = boundary_module.SandboxBoundary(tmp_path)
    boundary.sandbox_executable = tmp_path / "missing-sandbox-exec"
    reason = (
        "/usr/bin/sandbox-exec is unavailable"
        if boundary_module.platform.system() == "Darwin"
        else "the release-notes evaluator currently requires macOS sandbox-exec"
    )

    assert boundary.describe() == {
        "available": False,
        "mechanism": "unavailable",
        "defaultPolicy": "deny",
        "network": "deny",
        "childProcess": "deny-fork",
        "workspace": "read-only",
        "privateEvaluator": "not allowlisted",
        "reason": reason,
    }
    with pytest.raises(boundary_module.SandboxUnavailable):
        boundary.command([sys.executable, "-c", "pass"])


def test_manifest_attestation_detects_candidate_tampering(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    artifact = workspace / "scripts" / "harnessctl.py"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("print('original')\n", encoding="utf-8")
    manifest = workspace / ".hdp" / "manifest.json"
    manifest.parent.mkdir()
    manifest.write_text(
        json.dumps(
            {
                "artifacts": [
                    {
                        "path": "scripts/harnessctl.py",
                        "sha256": boundary_module.sha256_file(artifact),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert boundary_module.inspect_manifest(workspace)["valid"] is True
    artifact.write_text("print('candidate replacement')\n", encoding="utf-8")
    attestation = boundary_module.inspect_manifest(workspace)
    assert attestation["valid"] is False
    assert attestation["errors"] == [
        "manifest artifact 'scripts/harnessctl.py' digest mismatch"
    ]


def test_ledger_attestation_verifies_logs_and_detects_tampering(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    logs = workspace / "evidence" / "logs"
    logs.mkdir(parents=True)
    stdout = logs / "0001.stdout.log"
    stderr = logs / "0001.stderr.log"
    stdout.write_text("ok\n", encoding="utf-8")
    stderr.write_bytes(b"")
    record = {
        "sequence": 1,
        "command": ["python3", "-m", "unittest"],
        "requirementIds": ["REQ-PROCESS-VERIFY"],
        "exitCode": 0,
        "stdout": {
            "path": "evidence/logs/0001.stdout.log",
            "sha256": boundary_module.sha256_file(stdout),
        },
        "stderr": {
            "path": "evidence/logs/0001.stderr.log",
            "sha256": boundary_module.sha256_file(stderr),
        },
    }
    ledger = workspace / "evidence" / "ledger.jsonl"
    ledger.write_text(json.dumps(record) + "\n", encoding="utf-8")

    attestation = boundary_module.inspect_ledger(
        workspace,
        required_requirement_id="REQ-PROCESS-VERIFY",
        required_command_fragment=["-m", "unittest"],
    )
    assert attestation["valid"] is True
    assert len(attestation["verifiedLogDigests"]) == 2

    stdout.write_text("tampered\n", encoding="utf-8")
    attestation = boundary_module.inspect_ledger(
        workspace,
        required_requirement_id="REQ-PROCESS-VERIFY",
        required_command_fragment=["-m", "unittest"],
    )
    assert attestation["valid"] is False
    assert "ledger record 1 stdout digest mismatch" in attestation["errors"]


def test_safe_workspace_file_rejects_symlink_escape(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    (workspace / "escape.txt").symlink_to(outside)

    path, error = boundary_module.safe_workspace_file(workspace, "escape.txt")
    assert path is None
    assert error == "path traverses a symlink"
