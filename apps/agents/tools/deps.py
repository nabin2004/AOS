from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ir.manim_ir import Quality


@dataclass
class ToolDeps:
    """Runtime dependencies for tools that need filesystem or Docker access."""

    workspace_dir: Path
    docker_image: str = "manimcommunity/manim"
    # Reuse one long-lived container per workspace (via `docker exec`) instead
    # of paying container-startup cost on every render. See
    # tools/render.py and the "Manim render performance" section of README.md.
    persistent_container: bool = True

    def __post_init__(self) -> None:
        self.workspace_dir = Path(self.workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)


QUALITY_TO_MANIM_FLAG: dict[Quality, str] = {
    Quality.LOW: "l",
    Quality.MEDIUM: "m",
    Quality.HIGH: "h",
    Quality.PRODUCTION: "p",
    Quality.FOURK: "k",
}
