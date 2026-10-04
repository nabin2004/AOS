"""Vector diagram component for projections and vector arithmetic."""

from __future__ import annotations

from typing import Any

import numpy as np
from manim import Arrow, DashedLine

from motiongram.slides.diagrams.base import SlideDiagram


class VectorDiagram(SlideDiagram):
    """Vector coordinate plane with vectors and dashed projection lines."""

    def __init__(
        self,
        vectors: list[dict[str, Any]],
        show_projection: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        origin = np.array([0.0, 0.0, 0.0])
        vec_mobs: dict[str, Arrow] = {}

        for vec in vectors:
            v_id = vec.get("id", "vec")
            coords = vec.get("coords", [2.0, 1.0])
            color = vec.get("color", "#58C4DD")
            target_pt = np.array([coords[0], coords[1], 0.0])

            arr = Arrow(origin, target_pt, buff=0, color=color, stroke_width=4)
            self.add(arr)
            vec_mobs[v_id] = arr
            self.register_selector(f"vector[{v_id}]", arr)

        # Projection from v2 onto v1 if requested
        if show_projection and len(vectors) >= 2:
            p1 = np.array(vectors[0].get("coords", [2.0, 0.0]) + [0.0])
            p2 = np.array(vectors[1].get("coords", [1.0, 2.0]) + [0.0])
            # Projection point calculation
            u1 = p1 / np.linalg.norm(p1)
            proj_pt = np.dot(p2, u1) * u1
            d_line = DashedLine(p2, proj_pt, color="#888888")
            self.add(d_line)
            self.register_selector("projection", d_line)
