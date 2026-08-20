import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "run_local_verification.py"
SPEC = importlib.util.spec_from_file_location("run_local_verification", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_portable_argument_removes_repository_and_evidence_absolute_paths(tmp_path: Path) -> None:
    repository_file = MODULE.PROJECT / "examples" / "minimal" / "hdp.yaml"
    evidence_file = tmp_path / "work" / "generated-harness"

    assert MODULE.portable_argument(str(repository_file), tmp_path) == (
        "$REPOSITORY/examples/minimal/hdp.yaml"
    )
    assert MODULE.portable_argument(str(evidence_file), tmp_path) == (
        "$EVIDENCE/work/generated-harness"
    )
    assert MODULE.portable_argument("pytest", tmp_path) == "pytest"
    assert MODULE.portable_argument(MODULE.sys.executable, tmp_path).startswith(
        "$REPOSITORY/.venv/bin/python"
    )


def test_portable_log_replaces_machine_local_roots(tmp_path: Path) -> None:
    value = (
        f"source={MODULE.PROJECT}/examples/minimal/hdp.yaml\n"
        f"output={tmp_path}/work/generated-harness\n"
    )

    assert MODULE.portable_log(value, tmp_path) == (
        "source=$REPOSITORY/examples/minimal/hdp.yaml\n"
        "output=$EVIDENCE/work/generated-harness\n"
    )
