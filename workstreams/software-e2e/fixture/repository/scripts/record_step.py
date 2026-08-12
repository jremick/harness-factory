#!/usr/bin/env python3
"""Record required process evidence in strict order. Trace: HDP-5F37BB1FEA89AAC4."""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACE_ID = "HDP-5F37BB1FEA89AAC4"
REQUIRED = ["inspect-task", "inspect-tests", "implement", "verify"]
EVENTS = ROOT / "evidence" / "process-events.jsonl"

def read_events():
    if not EVENTS.exists():
        return []
    events = []
    for line_number, line in enumerate(EVENTS.read_text(encoding="utf-8").splitlines(), 1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid process evidence at line {line_number}: {exc}") from exc
        events.append(event)
    return events

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("step_id", choices=REQUIRED)
    parser.add_argument("--note", default="completed")
    args = parser.parse_args()
    if len(args.note) > 500 or "\n" in args.note or "\r" in args.note:
        print("DENY: note must be one line and at most 500 characters", file=sys.stderr)
        return 3
    try:
        existing = read_events()
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    actual = [event.get("step_id") for event in existing if event.get("event") == "step"]
    expected_next = REQUIRED[len(actual)] if len(actual) < len(REQUIRED) else None
    if args.step_id != expected_next:
        print(f"FAIL: next required step is {expected_next!r}, not {args.step_id!r}", file=sys.stderr)
        return 2
    event = {"event": "step", "note": args.note, "step_id": args.step_id, "trace_id": TRACE_ID}
    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in existing + [event]]
    fd, temporary = tempfile.mkstemp(prefix=".process-", dir=EVENTS.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        os.replace(temporary, EVENTS)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(f"RECORDED: {args.step_id}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
