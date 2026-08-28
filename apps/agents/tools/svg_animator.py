"""Manim SVG Integration and Animation Tool Module.

Parses OmniSVG XML strings or vector path files into Manim SVGMobject instances,
aligns spatial viewbox coordinates, and provides animation utilities (Create, DrawBorderThenFill).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional, Tuple, Any


class ManimSVGAnimator:
    """Helper to convert OmniSVG outputs to Manim SVGMobject and generate scene animations."""

    def __init__(self, default_target_height: float = 4.0):
        self.default_target_height = default_target_height

    def create_svg_mobject(self, svg_content_or_path: str, scale_to_height: Optional[float] = None) -> Any:
        """Parses SVG string or file path into a Manim SVGMobject."""
        try:
            from manim import SVGMobject
        except ImportError:
            raise ImportError("Manim Community Edition is required to instantiate SVGMobject.")

        target_h = scale_to_height or self.default_target_height

        # Check if input is a valid file path
        path = Path(svg_content_or_path)
        if path.exists() and path.is_file():
            svg_mob = SVGMobject(str(path))
        else:
            # Write SVG string to temporary file for SVGMobject parsing
            with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False, encoding="utf-8") as tmp:
                tmp.write(svg_content_or_path)
                tmp_path = tmp.name

            try:
                svg_mob = SVGMobject(tmp_path)
            finally:
                if Path(tmp_path).exists():
                    Path(tmp_path).unlink()

        # Rescale viewbox coordinates to fit Manim screen nicely
        if target_h > 0:
            svg_mob.scale_to_fit_height(target_h)

        return svg_mob

    def generate_animation_code(
        self,
        variable_name: str,
        svg_file_path: str,
        animation_type: str = "Create",
        run_time: float = 2.0,
    ) -> str:
        """Generates executable Python code string for Manim scene construct()."""
        valid_animations = {"Create", "DrawBorderThenFill", "FadeIn", "Write"}
        anim = animation_type if animation_type in valid_animations else "Create"

        code_lines = [
            f"{variable_name} = SVGMobject(r'{svg_file_path}')",
            f"{variable_name}.scale_to_fit_height({self.default_target_height})",
            f"{variable_name}.move_to(ORIGIN)",
            f"self.play({anim}({variable_name}), run_time={run_time})",
        ]
        return "\n".join(code_lines)
