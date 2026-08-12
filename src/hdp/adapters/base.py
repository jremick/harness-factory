"""Target adapter protocol and compilation records."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict

from ..hir import HIR


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PlannedArtifact(Record):
    path: str
    media_type: str
    executable: bool = False
    source_pointers: tuple[str, ...]
    transformation: str


class CompilePlan(Record):
    plan_version: str = "0.1.0"
    adapter: str
    adapter_version: str
    hir_digest: str
    artifacts: tuple[PlannedArtifact, ...]
    synthesis_requests: tuple[dict[str, Any], ...] = ()


class ConformanceResult(Record):
    status: str
    checks: tuple[dict[str, Any], ...]


class TargetAdapter(Protocol):
    name: str
    version: str

    def plan(self, hir: HIR) -> CompilePlan: ...
    def render(self, hir: HIR, output: Path) -> dict[str, Any]: ...
    def static_check(self, output: Path, hir: HIR) -> ConformanceResult: ...
