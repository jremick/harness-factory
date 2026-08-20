import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "run_reference_e2e.py"
SPEC = importlib.util.spec_from_file_location("run_reference_e2e", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
task_aggregate = MODULE.task_aggregate


def test_task_aggregate_binds_exactly_one_harness_result() -> None:
    subject = {
        "definition": {"id": "urn:test", "sha256": "b" * 64},
        "hir": {"sha256": "a" * 64},
        "binding": {"target": "codex", "sha256": "c" * 64},
        "harness": {"sha256": "d" * 64},
    }
    aggregate = {
        "schemaVersion": "0.1.0",
        "compilation": {"hir_digest": "a" * 64, "output": "/private/tmp/private"},
        "subject": subject,
        "environment": {"model": "gpt-5.6-sol"},
        "results": [
            {
                "task": "feature", "mode": "harness", "passed": True,
                "artifacts": "/private/tmp/private",
            },
            {"task": "feature", "mode": "baseline", "passed": False},
            {"task": "refactor", "mode": "harness", "passed": True},
        ],
    }

    projected = task_aggregate(aggregate, "feature")

    assert projected["passed"] is True
    assert projected["definitionOfDoneBehaviouralGate"] == "pass"
    assert [item["mode"] for item in projected["results"]] == ["harness", "baseline"]
    assert projected["compilation"] == {"hir_digest": "a" * 64}
    assert projected["subject"] == subject
    assert "artifacts" not in projected["results"][0]
    assert "/private/tmp/private" not in repr(projected)


def test_task_aggregate_fails_on_missing_or_duplicate_harness_result() -> None:
    missing = {"schemaVersion": "0.1.0", "results": []}
    duplicate = {
        "schemaVersion": "0.1.0",
        "results": [
            {"task": "feature", "mode": "harness", "passed": True},
            {"task": "feature", "mode": "harness", "passed": True},
        ],
    }

    assert task_aggregate(missing, "feature")["passed"] is False
    assert task_aggregate(duplicate, "feature")["passed"] is False
