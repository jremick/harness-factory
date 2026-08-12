"""Render deterministic Markdown release notes."""

from typing import Any, Mapping, Sequence


def build_release_notes(changes: Sequence[Mapping[str, Any]]) -> str:
    """Build release notes according to TASK.md."""

    raise NotImplementedError("Implement build_release_notes")

