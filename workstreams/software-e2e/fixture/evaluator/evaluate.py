#!/usr/bin/env python3
"""Run evaluator-owned checks against a candidate repository."""

from __future__ import annotations

import argparse
import os
import sys
import unittest
from pathlib import Path


CANARY_MARKER = "HDP_" + "EVALUATOR_CANARY_59d95bda50a7"


def assert_canary_absent(target: Path) -> None:
    for path in target.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if CANARY_MARKER in content:
            raise AssertionError(f"evaluator marker leaked into candidate file: {path.relative_to(target)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    target = args.target.resolve()
    if not (target / "src" / "inventory.py").is_file():
        print("EVALUATOR FAIL: candidate repository is missing src/inventory.py", file=sys.stderr)
        return 2
    try:
        assert_canary_absent(target)
    except AssertionError as exc:
        print(f"EVALUATOR FAIL: {exc}", file=sys.stderr)
        return 2
    os.environ["HDP_EVAL_TARGET"] = str(target)
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent), pattern="test_hidden.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        print(f"EVALUATOR PASS: {result.testsRun} independent tests")
        return 0
    print(f"EVALUATOR FAIL: {result.testsRun} independent tests", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

