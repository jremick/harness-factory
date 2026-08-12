#!/usr/bin/env python3
"""Create a bounded, content-digest inventory of likely harness artifacts."""

import argparse
import hashlib
import json
from pathlib import Path


SKIP = {".git", ".venv", "node_modules", "dist", "build", "__pycache__"}
TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".py", ".sh", ".js", ".mjs", ".ts"}
MAX_BYTES = 1024 * 1024


def classify(path: Path) -> str:
    value = path.as_posix().lower()
    if path.name in {"AGENTS.md", "CLAUDE.md", "SYSTEM.md", "DEVELOPER.md"}:
        return "instruction"
    if path.name == "SKILL.md" or "/skills/" in f"/{value}":
        return "agent-skill"
    if "test" in value or "eval" in value:
        return "test-or-evaluator"
    if ".github/workflows/" in value:
        return "ci-cd"
    if "hook" in value or "middleware" in value:
        return "hook-or-middleware"
    if "mcp" in value or "openapi" in value or "tool" in value:
        return "tool-interface"
    if "deploy" in value or "docker" in value or path.name == "vercel.json":
        return "deployment-runtime"
    if "memory" in value or "state" in value or "context" in value:
        return "state-context-memory"
    return "implementation-or-documentation"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("harness", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.harness.resolve()
    if not root.is_dir():
        parser.error(f"not a directory: {root}")
    files = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in SKIP for part in relative.parts):
            continue
        if path.is_symlink():
            files.append({"path": relative.as_posix(), "kind": "symlink", "inspected": False})
            continue
        if not path.is_file():
            continue
        content = path.read_bytes()
        files.append(
            {
                "path": relative.as_posix(),
                "kind": classify(relative),
                "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "textCandidate": path.suffix.lower() in TEXT_SUFFIXES,
                "inspectable": len(content) <= MAX_BYTES,
            }
        )
    report = {"schemaVersion": "1", "root": str(root), "files": files}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"fileCount": len(files), "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

