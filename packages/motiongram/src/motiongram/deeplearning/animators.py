"""Timeline animators for deep-learning node properties."""

from __future__ import annotations

from dataclasses import dataclass

from motiongram.animate import lerp
from motiongram.core import Node


@dataclass(slots=True)
class AnimateAttribute:
    """Linearly interpolate any float attribute on a node (``progress``, ``x_val``, etc.)."""

    attr: str
    v0: float
    v1: float

    def apply(self, node: Node, t: float) -> None:
        setattr(node, self.attr, lerp(self.v0, self.v1, t))


@dataclass(slots=True)
class AnimateIntAttribute:
    """Round interpolated float to int (``active_row``, ``active_col``, ``active_idx``)."""

    attr: str
    v0: int
    v1: int

    def apply(self, node: Node, t: float) -> None:
        val = int(round(lerp(float(self.v0), float(self.v1), t)))
        setattr(node, self.attr, val)
