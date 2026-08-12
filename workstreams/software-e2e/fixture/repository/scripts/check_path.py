#!/usr/bin/env python3
"""Fail-closed repository write-scope guard. Trace: HDP-5F37BB1FEA89AAC4."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = ["src", "tests"]
PROHIBITED = [".git", ".hdp", ".agents", "AGENTS.md", "TASK.md", "evidence", "scripts"]

def contained(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
        return True
    except ValueError:
        return False

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", required=True)
    args = parser.parse_args()
    raw = Path(args.write)
    if raw.is_absolute():
        print("DENY: absolute write paths are forbidden", file=sys.stderr)
        return 3
    candidate = (ROOT / raw).resolve(strict=False)
    if not contained(candidate, ROOT):
        print("DENY: write resolves outside repository root", file=sys.stderr)
        return 3
    for item in PROHIBITED:
        if contained(candidate, (ROOT / item).resolve(strict=False)):
            print(f"DENY: write is inside prohibited path {item}", file=sys.stderr)
            return 3
    if not any(contained(candidate, (ROOT / item).resolve(strict=False)) for item in ALLOWED):
        print("DENY: write is outside the allowlisted paths", file=sys.stderr)
        return 3
    print(f"ALLOW: {candidate.relative_to(ROOT)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
