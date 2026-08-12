#!/usr/bin/env python3
"""Execute the fixture through an existing non-interactive Codex CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path


WORKSTREAM = Path(__file__).resolve().parents[1]
FIXTURE = WORKSTREAM / "fixture"
sys.path.insert(0, str(WORKSTREAM))

import hdpgen  # noqa: E402


PROMPT = """Execute the already-approved task in this repository now.
Read AGENTS.md, AGENTS.local.md, and TASK.md. Implement the requested behavior,
follow every required process/evidence step, and finish by running the generated
verification and completion gates. Work only inside this workspace. Do not read
or write parent or sibling paths, use network access, inspect credentials, or
seek hidden evaluation material. Proceed without asking for plan approval.
"""


def hash_tree(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def remove_write_bits(root: Path) -> None:
    for path in sorted(root.rglob("*"), reverse=True):
        mode = stat.S_IMODE(path.stat().st_mode)
        path.chmod(mode & ~0o222)
    mode = stat.S_IMODE(root.stat().st_mode)
    root.chmod(mode & ~0o222)


def seal_evaluator(root: Path) -> list[tuple[Path, int]]:
    """Make evaluator contents unreadable/unwritable during the agent process."""

    entries = [(root, stat.S_IMODE(root.stat().st_mode))]
    entries.extend((path, stat.S_IMODE(path.stat().st_mode)) for path in root.rglob("*"))
    for path, _mode in sorted(entries, key=lambda item: len(item[0].parts), reverse=True):
        path.chmod(0)
    return entries


def restore_evaluator(entries: list[tuple[Path, int]]) -> None:
    for path, mode in sorted(entries, key=lambda item: len(item[0].parts)):
        path.chmod(mode)


def command_text(argv: list[str]) -> str:
    import shlex

    return " ".join(shlex.quote(item) for item in argv) + "\n"


def run_capture(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=480)
    args = parser.parse_args()
    run_root = args.output.resolve()
    if run_root.exists():
        print(f"RUNNER ERROR: output already exists: {run_root}", file=sys.stderr)
        return 2
    if not 30 <= args.timeout_seconds <= 1800:
        print("RUNNER ERROR: timeout must be from 30 to 1800 seconds", file=sys.stderr)
        return 2

    workspace = run_root / "workspace"
    evaluator = run_root / "evaluator"
    artifacts = run_root / "artifacts"
    shutil.copytree(FIXTURE / "repository", workspace)
    shutil.copytree(FIXTURE / "evaluator", evaluator)
    artifacts.mkdir(parents=True)
    remove_write_bits(evaluator)
    boundary_before = hash_tree(evaluator)

    try:
        manifest = hdpgen.generate(FIXTURE / "harness.yaml", workspace)
    except hdpgen.HDPError as exc:
        (artifacts / "summary.json").write_text(
            json.dumps({"blocker": f"generation failed: {exc}"}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"RUNNER ERROR: generation failed: {exc}", file=sys.stderr)
        return 2

    init = run_capture(["git", "init", "-q"], workspace)
    if init.returncode != 0:
        print(f"RUNNER ERROR: git init failed: {init.stderr.strip()}", file=sys.stderr)
        return 2
    run_capture(["git", "add", "-A"], workspace)
    commit = run_capture(
        [
            "git",
            "-c",
            "user.name=HDP Evaluator",
            "-c",
            "user.email=hdp-evaluator@example.invalid",
            "commit",
            "-q",
            "-m",
            "fixture baseline",
        ],
        workspace,
    )
    if commit.returncode != 0:
        print(f"RUNNER ERROR: baseline commit failed: {commit.stderr.strip()}", file=sys.stderr)
        return 2

    codex = shutil.which("codex")
    summary: dict[str, object] = {
        "boundary_unchanged": False,
        "codex_exit_code": None,
        "completion_gate": False,
        "evaluator_exit_code": None,
        "execution_mode": "default",
        "trace_id": manifest["trace_id"],
    }
    if codex is None:
        summary["blocker"] = "No 'codex' executable was found on PATH; no authentication path was attempted."
        (artifacts / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(summary["blocker"], file=sys.stderr)
        return 3

    last_message = artifacts / "last-message.txt"
    argv = [
        codex,
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--sandbox",
        "workspace-write",
        "--cd",
        str(workspace),
        "--skip-git-repo-check",
        "--json",
        "--output-last-message",
        str(last_message),
    ]
    argv.append("-")
    (artifacts / "command.txt").write_text(command_text(argv), encoding="utf-8")
    (artifacts / "prompt.txt").write_text(PROMPT, encoding="utf-8")

    sealed_entries = seal_evaluator(evaluator)
    try:
        with (artifacts / "codex.jsonl").open("w", encoding="utf-8") as stdout_handle, (
            artifacts / "codex.stderr.log"
        ).open("w", encoding="utf-8") as stderr_handle:
            try:
                completed = subprocess.run(
                    argv,
                    cwd=WORKSTREAM,
                    input=PROMPT,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    text=True,
                    timeout=args.timeout_seconds,
                    check=False,
                )
                summary["codex_exit_code"] = completed.returncode
            except subprocess.TimeoutExpired:
                summary["blocker"] = f"codex exec exceeded the {args.timeout_seconds}-second runner limit"
                summary["codex_exit_code"] = 124
    finally:
        restore_evaluator(sealed_entries)

    boundary_after = hash_tree(evaluator)
    summary["boundary_unchanged"] = boundary_before == boundary_after
    (artifacts / "evaluator-hashes-before.json").write_text(
        json.dumps(boundary_before, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (artifacts / "evaluator-hashes-after.json").write_text(
        json.dumps(boundary_after, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    evaluation = run_capture(["python3", str(evaluator / "evaluate.py"), str(workspace)], run_root)
    summary["evaluator_exit_code"] = evaluation.returncode
    (artifacts / "evaluator-result.txt").write_text(
        evaluation.stdout + evaluation.stderr, encoding="utf-8"
    )
    diff = run_capture(["git", "diff", "--no-ext-diff", "--binary"], workspace)
    status = run_capture(["git", "status", "--short"], workspace)
    (artifacts / "workspace.diff").write_text(diff.stdout, encoding="utf-8")
    (artifacts / "workspace-status.txt").write_text(status.stdout, encoding="utf-8")

    completion_path = workspace / "evidence/completion.json"
    if completion_path.is_file():
        try:
            completion = json.loads(completion_path.read_text(encoding="utf-8"))
            summary["completion_gate"] = completion.get("complete") is True and completion.get("trace_id") == manifest["trace_id"]
        except (OSError, json.JSONDecodeError):
            summary["completion_gate"] = False

    combined = ""
    for log_path in (artifacts / "codex.stderr.log", artifacts / "codex.jsonl", last_message):
        try:
            combined += log_path.read_text(encoding="utf-8").lower()
        except OSError:
            pass
    if "blocker" not in summary and "timed out negotiating with the code-mode host" in combined:
        summary["blocker"] = (
            "Codex could not execute even read-only tools because negotiation with the "
            "code-mode host timed out; no repository changes were made."
        )
    elif "blocker" not in summary and "code-mode host is disabled" in combined:
        summary["blocker"] = (
            "Codex failed closed because the code-mode host was disabled; disabling the "
            "host is not a usable fallback execution path."
        )
    elif "blocker" not in summary and (
        "authentication" in combined or "not logged in" in combined or "401 unauthorized" in combined
    ):
        summary["blocker"] = (
            "Existing Codex CLI authentication was unavailable or rejected; no new authentication was attempted."
        )
    elif "blocker" not in summary and summary["codex_exit_code"] not in (0, None):
        summary["blocker"] = f"codex exec exited {summary['codex_exit_code']}; inspect the preserved CLI logs"

    passed = (
        summary["codex_exit_code"] == 0
        and summary["evaluator_exit_code"] == 0
        and summary["completion_gate"] is True
        and summary["boundary_unchanged"] is True
    )
    summary["passed"] = passed
    if not passed and "blocker" not in summary:
        summary["blocker"] = (
            "The agent run finished but did not satisfy the generated completion and independent evaluator gates."
        )
    (artifacts / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
