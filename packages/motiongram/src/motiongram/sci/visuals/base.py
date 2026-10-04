"""Base interface for scientific visual components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from motiongram.sci.schema import VisualComponentSpec
from motiongram.sci.solvers.base import DataResult


class VisualComponent(ABC):
    """Abstract base class for visual mobjects consuming scientific data."""

    def __init__(self, spec: VisualComponentSpec):
        self.spec = spec

    @abstractmethod
    def build(self, data: DataResult, coordinate_system: Any, style: dict[str, Any]) -> Any:
        """Construct and return the Manim mobject representing the data."""
