#!/usr/bin/env python3
"""Run locally deterministic factory gates and preserve machine-readable evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT = Path(__file__).resolve().parents[1]
EXAMPLE = PROJECT / "examples/software-development/hdp.yaml"
BINDING = PROJECT / "examples/software-development/bindings/codex.yaml"


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture_version(argv: list[str]) -> str:
    result = subprocess.run(argv, cwd=PROJECT, capture_output=True, text=True, check=False)
    output = (result.stdout or result.stderr).strip()
    return output.splitlines()[0] if output else "unavailable"


def run_gate(
    gate_id: str,
    argv: list[str],
    evidence: Path,
    *,
    expected: set[int] | None = None,
) -> dict[str, Any]:
    expected = expected or {0}
    started = time.monotonic()
    result = subprocess.run(argv, cwd=PROJECT, capture_output=True, text=True, check=False)
    stdout = evidence / "logs" / f"{gate_id}.stdout.log"
    stderr = evidence / "logs" / f"{gate_id}.stderr.log"
    stdout.write_text(result.stdout, encoding="utf-8")
    stderr.write_text(result.stderr, encoding="utf-8")
    return {
        "id": gate_id,
        "command": argv,
        "exitCode": result.returncode,
        "expectedExitCodes": sorted(expected),
        "passed": result.returncode in expected,
        "durationSeconds": round(time.monotonic() - started, 3),
        "stdout": {"path": str(stdout.relative_to(evidence)), "sha256": sha256(stdout)},
        "stderr": {"path": str(stderr.relative_to(evidence)), "sha256": sha256(stderr)},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = args.output.resolve()
    if evidence.exists():
        print(f"output already exists: {evidence}", file=sys.stderr)
        return 2
    evidence.mkdir(parents=True)
    (evidence / "logs").mkdir()
    work = evidence / "work"
    harness = work / "generated-harness"
    analysis = work / "analysis"
    release = work / "release"
    executable = sys.executable
    hdp_executable = str(Path(executable).with_name("hdp"))
    cli = [hdp_executable]

    gates = [
        run_gate("pytest", [executable, "-m", "pytest", "-q"], evidence),
        run_gate("validate", [*cli, "validate", str(EXAMPLE), "--json"], evidence),
        run_gate(
            "compile",
            [*cli, "compile", str(EXAMPLE), "--binding", str(BINDING), "--output", str(harness)],
            evidence,
        ),
        run_gate(
            "static-conformance",
            [
                *cli, "test", str(harness), "--definition", str(EXAMPLE),
                "--binding", str(BINDING),
            ],
            evidence,
        ),
        run_gate("analyse", [*cli, "analyse", str(harness), "--output", str(analysis)], evidence),
        run_gate("round-trip-diff", [*cli, "diff", str(EXAMPLE), str(analysis / "hdp.reconstructed.yaml")], evidence),
        run_gate(
            "package-ineligible",
            [*cli, "package", str(harness), "--definition", str(EXAMPLE), "--binding", str(BINDING), "--output", str(release)],
            evidence,
        ),
        run_gate("verify-release", [*cli, "verify-release", str(release)], evidence),
    ]
    tampered = work / "release-tampered"
    if release.is_dir():
        shutil.copytree(release, tampered)
        card = tampered / "payload/harness/HarnessCard.md"
        if card.is_file():
            card.write_text(card.read_text(encoding="utf-8") + "tampered-after-package\n", encoding="utf-8")
        gates.append(run_gate(
            "tamper-detected", [*cli, "verify-release", str(tampered)], evidence, expected={2},
        ))

    finished = datetime.now(timezone.utc).isoformat()
    report = {
        "schemaVersion": "0.1.0",
        "kind": "LocalVerificationEvidence",
        "passed": bool(gates) and all(item["passed"] for item in gates),
        "releaseEligible": False,
        "releaseEligibilityReason": "live behavioural conformance is a separate mandatory gate",
        "recordedAt": finished,
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "uv": capture_version(["uv", "--version"]),
            "git": capture_version(["git", "--version"]),
            "docker": capture_version(["docker", "--version"]),
            "modelExecution": "not-applicable-local-deterministic-gates",
        },
        "gates": gates,
        "artifacts": {
            "generatedHarness": str(harness.relative_to(evidence)),
            "analysis": str(analysis.relative_to(evidence)),
            "release": str(release.relative_to(evidence)),
            "tamperedRelease": str(tampered.relative_to(evidence)),
        },
    }
    (evidence / "verification.json").write_text(dump(report), encoding="utf-8")
    print(dump(report), end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
