"""Small inventory domain used by the HDP end-to-end fixture."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class StockItem:
    sku: str
    quantity: int


def reorder_candidates(items: Iterable[StockItem], threshold: int = 5) -> list[str]:
    """Return SKUs that should be reordered.

    The behavior is intentionally unfinished. See TASK.md.
    """

    raise NotImplementedError("implement the behavior described in TASK.md")

