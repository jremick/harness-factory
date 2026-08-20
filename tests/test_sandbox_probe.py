import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "run_sandbox_probe.py"
SPEC = importlib.util.spec_from_file_location("run_sandbox_probe", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
evaluate_probe_results = MODULE.evaluate_probe_results
portable_argument = MODULE.portable_argument


def test_sandbox_probe_requires_denials_and_inside_success() -> None:
    probes = evaluate_probe_results(
        [
            {"id": "outside-workspace-read", "succeeded": False, "observed": "PermissionError"},
            {"id": "network-tcp-connect", "succeeded": False, "observed": "PermissionError"},
            {"id": "inside-workspace-write-read", "succeeded": True, "observed": "INSIDE_OK"},
        ]
    )
    assert all(item["passed"] for item in probes)


def test_sandbox_probe_fails_open_network_and_missing_results() -> None:
    probes = evaluate_probe_results(
        [
            {"id": "network-tcp-connect", "succeeded": True, "observed": "None"},
            {"id": "inside-workspace-write-read", "succeeded": True, "observed": "INSIDE_OK"},
        ]
    )
    assert not all(item["passed"] for item in probes)


def test_sandbox_probe_command_projection_removes_evidence_path(tmp_path: Path) -> None:
    assert portable_argument(str(tmp_path / "workspace" / "result.json"), tmp_path) == (
        "$EVIDENCE/workspace/result.json"
    )
