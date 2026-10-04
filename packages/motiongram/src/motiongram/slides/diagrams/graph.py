"""Graph diagram component for functions, axes, and areas."""

from __future__ import annotations

from typing import Any

from manim import Axes

from motiongram.slides.diagrams.base import SlideDiagram


class GraphDiagram(SlideDiagram):
    """2D Cartesian axes with plotted curve and shaded area."""

    def __init__(
        self,
        x_range: list[float] | None = None,
        y_range: list[float] | None = None,
        x_length: float = 7.0,
        y_length: float = 4.0,
        function_str: str = "x**2",
        area_range: list[float] | None = None,
        curve_color: str = "#FFFF00",
        area_color: str = "#58C4DD",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        axes = Axes(
            x_range=x_range or [-3, 3, 1],
            y_range=y_range or [0, 9, 2],
            x_length=x_length,
            y_length=y_length,
            axis_config={"color": "#888888"},
        )
        self.add(axes)
        self.register_selector("axes", axes)

        # Plot function
        try:
            def fn(x: float) -> float:
                return float(eval(function_str, {"x": x, "__builtins__": {}}))

            curve = axes.plot(fn, color=curve_color)
            self.add(curve)
            self.register_selector("curve", curve)

            if area_range and len(area_range) >= 2:
                area = axes.get_area(
                    curve,
                    x_range=[area_range[0], area_range[1]],
                    color=area_color,
                    opacity=0.4,
                )
                self.add(area)
                self.register_selector("area", area)
        except Exception:
            pass
