#!/usr/bin/env python3
"""Run definition-owned verification without a shell. Trace: HDP-5F37BB1FEA89AAC4."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACE_ID = "HDP-5F37BB1FEA89AAC4"
COMMANDS = json.loads("[{\"argv\":[\"python3\",\"-m\",\"unittest\",\"discover\",\"-s\",\"tests\",\"-v\"],\"cwd\":\".\",\"id\":\"public-tests\",\"timeout_seconds\":60},{\"argv\":[\"python3\",\"-m\",\"compileall\",\"-q\",\"src\",\"tests\"],\"cwd\":\".\",\"id\":\"syntax\",\"timeout_seconds\":30}]")
RESULTS = ROOT / "evidence" / "verification-results.json"
OUTPUT_LIMIT = 20000

def contained(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
        return True
    except ValueError:
        return False

def limited(value: str) -> str:
    if len(value) <= OUTPUT_LIMIT:
        return value
    return value[:OUTPUT_LIMIT] + "\n...[truncated by harness]\n"

def main() -> int:
    results = []
    clean_env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    for check in COMMANDS:
        cwd = (ROOT / check["cwd"]).resolve(strict=False)
        if not contained(cwd, ROOT):
            result = {"id": check["id"], "passed": False, "reason": "cwd escaped repository"}
            results.append(result)
            continue
        try:
            completed = subprocess.run(
                check["argv"],
                cwd=cwd,
                env=clean_env,
                capture_output=True,
                text=True,
                timeout=check["timeout_seconds"],
                check=False,
            )
            result = {
                "argv": check["argv"],
                "id": check["id"],
                "passed": completed.returncode == 0,
                "returncode": completed.returncode,
                "stderr": limited(completed.stderr),
                "stdout": limited(completed.stdout),
            }
        except (OSError, subprocess.TimeoutExpired) as exc:
            result = {"id": check["id"], "passed": False, "reason": type(exc).__name__}
        results.append(result)
        print(f"{'PASS' if result['passed'] else 'FAIL'}: {check['id']}")

    payload = {"checks": results, "trace_id": TRACE_ID}
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".verification-", dir=RESULTS.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, RESULTS)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return 0 if all(item["passed"] for item in results) else 1

if __name__ == "__main__":
    raise SystemExit(main())
