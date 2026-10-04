"""Base interfaces and data structures for scientific solvers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from motiongram.sci.schema import DataSourceSpec


@dataclass
class DataResult:
    """Numerical result computed by a scientific data source."""

    points: np.ndarray
    time: np.ndarray | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "success"
    error: str | None = None

    def validate(self) -> None:
        """Validate result contains no NaNs or infinities."""
        if not np.all(np.isfinite(self.points)):
            raise ValueError("DataResult contains NaN or Inf values in points.")
        if self.time is not None and not np.all(np.isfinite(self.time)):
            raise ValueError("DataResult contains NaN or Inf values in time array.")


class DataSource(ABC):
    """Abstract base class for all scientific data generators and solvers."""

    @abstractmethod
    def solve(self, spec: DataSourceSpec, quality: str = "final") -> DataResult:
        """Execute calculation and return numerical data result."""

    @abstractmethod
    def cache_key(self, spec: DataSourceSpec, quality: str = "final") -> str:
        """Calculate deterministic content hash for caching."""
