"""Canvas protocol: backends implement drawing primitives nodes need (no timeline)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@runtime_checkable
class Canvas(Protocol):
    """Minimal surface passed to ``Node.draw``; ASCII/Skia backends provide this."""

    def set_pixel(self, x: int, y: int, ch: str = "#") -> None:
        """Plot one sample at integer grid coordinates."""


class NullCanvas:
    """No-op raster canvas (dummy backend — timeline still drives nodes)."""

    __slots__ = ()

    def set_pixel(self, x: int, y: int, ch: str = "#") -> None:
        _ = x, y, ch


@dataclass
class RecordingCanvas:
    """Record ``set_pixel`` calls for assertions (tests / debugging)."""

    ops: list[tuple[int, int, str]] = field(default_factory=list)

    def set_pixel(self, x: int, y: int, ch: str = "#") -> None:
        self.ops.append((x, y, ch[0] if ch else ""))
