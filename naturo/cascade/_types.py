"""Data classes for cascade results and statistics."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from naturo.backends.base import ElementInfo


@dataclass
class ProviderStat:
    """Per-provider statistics."""
    name: str
    elements: int = 0
    elapsed_ms: float = 0.0
    status: str = "ok"  # ok | skipped | error


@dataclass
class CascadeStats:
    """Aggregated statistics from a cascade run."""
    providers: List[ProviderStat] = field(default_factory=list)
    total_elements: int = 0
    coverage_estimate: float = 0.0  # 0.0–1.0 (rough area coverage)

    def to_dict(self) -> dict:
        return {
            "total_elements": self.total_elements,
            "coverage_estimate": round(self.coverage_estimate, 3),
            "providers": [
                {
                    "name": p.name,
                    "elements": p.elements,
                    "elapsed_ms": round(p.elapsed_ms, 1),
                    "status": p.status,
                }
                for p in self.providers
            ],
        }


@dataclass
class CascadeResult:
    """Result from :func:`run_cascade`."""
    tree: Optional[ElementInfo]  # Root element (or None if nothing found)
    stats: CascadeStats
    primary_provider: str = "uia"  # Which provider produced the root tree
