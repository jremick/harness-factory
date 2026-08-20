#!/usr/bin/env python3
"""Fail closed on public-repository hygiene and local Markdown links."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "SUPPORT.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    ".github/workflows/ci.yml",
)
FORBIDDEN_TEXT = (
    "/Users/",
    "\\Users\\",
    "CasePilot",
    ".Trash/",
    "/Applications/",
    '"thread_id":',
    '"threadId":',
)
FORBIDDEN_TRACKED_PARTS = frozenset({".venv", "__pycache__", ".pytest_cache"})
MARKER_TEST_FILES = frozenset({
    "tests/test_compiler_packaging.py",
    "tools/check_public_surface.py",
})
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
ACTION = re.compile(r"^\s*uses:\s*([^\s@]+)@([^\s#]+)", re.MULTILINE)
SHA = re.compile(r"[0-9a-f]{40}")


def candidate_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / value.decode() for value in result.stdout.split(b"\0") if value]


def main() -> int:
    errors: list[str] = []
    paths = candidate_files()
    relative_paths = {path.relative_to(ROOT).as_posix() for path in paths}
    for required in REQUIRED:
        if required not in relative_paths or not (ROOT / required).is_file():
            errors.append(f"missing required public file: {required}")

    for path in paths:
        relative = path.relative_to(ROOT)
        if any(part in FORBIDDEN_TRACKED_PARTS for part in relative.parts):
            errors.append(f"forbidden tracked runtime path: {relative.as_posix()}")
            continue
        if not path.is_file() or path.is_symlink():
            if path.is_symlink():
                errors.append(f"tracked symlink requires explicit review: {relative.as_posix()}")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for marker in FORBIDDEN_TEXT:
            if marker in text and relative.as_posix() not in MARKER_TEST_FILES:
                errors.append(
                    f"private-machine marker {marker!r}: {relative.as_posix()}"
                )
        if path.suffix.lower() == ".md":
            for match in LINK.finditer(text):
                raw = match.group(1).strip().split(maxsplit=1)[0].strip("<>")
                target = unquote(raw.split("#", 1)[0])
                if not target or "://" in target or target.startswith(("mailto:", "#")):
                    continue
                destination = (
                    ROOT / target.lstrip("/")
                    if target.startswith("/")
                    else path.parent / target
                )
                if not destination.exists():
                    errors.append(
                        f"broken local Markdown link {raw!r}: {relative.as_posix()}"
                    )

    workflow = ROOT / ".github/workflows/ci.yml"
    if workflow.is_file():
        for action, revision in ACTION.findall(workflow.read_text(encoding="utf-8")):
            if SHA.fullmatch(revision) is None:
                errors.append(f"GitHub Action is not pinned to a commit: {action}@{revision}")

    if errors:
        for error in sorted(set(errors)):
            print(f"PUBLIC_SURFACE_FAIL {error}", file=sys.stderr)
        return 1
    print(f"PUBLIC_SURFACE_PASS checked {len(paths)} repository files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
