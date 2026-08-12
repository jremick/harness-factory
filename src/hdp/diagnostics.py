"""Stable diagnostics shared by structural and semantic validation."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Diagnostic:
    """A deterministic, machine-readable validation diagnostic."""

    code: str
    message: str
    instance_path: str = ""
    severity: str = "error"
    rule_id: Optional[str] = None
    related_paths: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HdpError(Exception):
    """Base class for expected HDP command failures."""


class HdpInputError(HdpError):
    """Raised when a source document cannot be parsed safely."""


class HdpGenerationError(HdpError):
    """Raised when generation cannot proceed safely."""

