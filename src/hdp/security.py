"""Deterministic secret-pattern checks for generated release inputs.

The scanner intentionally reports fingerprints and locations, never matched
values. It is a narrow release gate, not a claim that arbitrary credentials can
always be detected by pattern matching.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


MAX_SCANNED_FILE_BYTES = 2 * 1024 * 1024

_PATTERNS = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("github-token", re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9]{30,255}\b")),
    ("openai-token", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    (
        "credential-assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|"
            r"password|secret)\b\s*[:=]\s*[\"']?([A-Za-z0-9_./+=:@-]{20,})"
        ),
    ),
)


def _safe_artifact_paths(manifest: Mapping[str, Any]) -> Iterable[str]:
    for item in manifest.get("artifacts", []):
        relative = item.get("path") if isinstance(item, Mapping) else None
        if not isinstance(relative, str):
            continue
        pure = PurePosixPath(relative)
        if not pure.is_absolute() and ".." not in pure.parts:
            yield relative


def scan_generated_artifacts(root: Path, manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return redacted findings for manifest-listed text artifacts."""

    findings: list[dict[str, Any]] = []
    for relative in sorted(set(_safe_artifact_paths(manifest))):
        path = root / relative
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_SCANNED_FILE_BYTES:
            continue
        raw = path.read_bytes()
        if b"\x00" in raw:
            continue
        text = raw.decode("utf-8", errors="replace")
        for rule_id, pattern in _PATTERNS:
            for match in pattern.finditer(text):
                matched = match.group(1) if match.lastindex else match.group(0)
                findings.append({
                    "rule": rule_id,
                    "path": relative,
                    "line": text.count("\n", 0, match.start()) + 1,
                    "fingerprint": hashlib.sha256(matched.encode("utf-8")).hexdigest()[:16],
                })
    return findings
