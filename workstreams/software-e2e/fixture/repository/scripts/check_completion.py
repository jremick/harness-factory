#!/usr/bin/env python3
"""Gate completion on required process and verification evidence. Trace: HDP-5F37BB1FEA89AAC4."""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACE_ID = "HDP-5F37BB1FEA89AAC4"
REQUIRED_STEPS = ["inspect-task", "inspect-tests", "implement", "verify"]
REQUIRED_CHECKS = ["public-tests", "syntax"]
EVENTS = ROOT / "evidence" / "process-events.jsonl"
RESULTS = ROOT / "evidence" / "verification-results.json"
COMPLETION = ROOT / "evidence" / "completion.json"

def fail(message: str) -> int:
    print(f"INCOMPLETE: {message}", file=sys.stderr)
    return 2

def main() -> int:
    if not EVENTS.exists():
        return fail("missing process evidence")
    try:
        events = [json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines() if line]
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"invalid process evidence: {exc}")
    actual_steps = [item.get("step_id") for item in events if item.get("event") == "step"]
    if actual_steps != REQUIRED_STEPS:
        return fail(f"required steps {REQUIRED_STEPS!r}; observed {actual_steps!r}")
    if any(item.get("trace_id") != TRACE_ID for item in events):
        return fail("process trace mismatch")
    if not RESULTS.exists():
        return fail("missing verification results")
    try:
        verification = json.loads(RESULTS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"invalid verification results: {exc}")
    if verification.get("trace_id") != TRACE_ID:
        return fail("verification trace mismatch")
    checks = verification.get("checks")
    if not isinstance(checks, list):
        return fail("verification checks are missing")
    actual_checks = [item.get("id") for item in checks]
    if actual_checks != REQUIRED_CHECKS:
        return fail(f"required checks {REQUIRED_CHECKS!r}; observed {actual_checks!r}")
    failed = [item.get("id") for item in checks if item.get("passed") is not True]
    if failed:
        return fail("failed verification: " + ", ".join(str(item) for item in failed))
    payload = {"complete": True, "required_checks": REQUIRED_CHECKS, "required_steps": REQUIRED_STEPS, "trace_id": TRACE_ID}
    COMPLETION.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".completion-", dir=COMPLETION.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, COMPLETION)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(f"COMPLETE: {TRACE_ID}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
