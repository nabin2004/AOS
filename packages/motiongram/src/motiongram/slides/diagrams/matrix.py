"""Matrix diagram component with entry and bracket selectors."""

from __future__ import annotations

from typing import Any

from manim import Matrix, VGroup

from motiongram.slides.diagrams.base import SlideDiagram


class MatrixDiagram(SlideDiagram):
    """Formatted matrix exposing cell, row, and column selectors."""

    def __init__(
        self,
        values: list[list[Any]],
        bracket_color: str = "#58C4DD",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        # Create Manim matrix
        mat = Matrix(values, bracket_config={"color": bracket_color})
        self.add(mat)

        num_rows = len(values)
        num_cols = len(values[0]) if num_rows > 0 else 0

        # Submobjects structure in Manim Matrix:
        # mat.get_entries() gives flat list in row-major order
        entries = mat.get_entries()
        for r in range(num_rows):
            row_mobs = []
            for c in range(num_cols):
                idx = r * num_cols + c
                if idx < len(entries):
                    cell_mob = entries[idx]
                    row_mobs.append(cell_mob)
                    self.register_selector(f"entry[{r},{c}]", cell_mob)
            self.register_selector(f"row[{r}]", VGroup(*row_mobs))

        for c in range(num_cols):
            col_mobs = [
                entries[r * num_cols + c]
                for r in range(num_rows)
                if r * num_cols + c < len(entries)
            ]
            self.register_selector(f"col[{c}]", VGroup(*col_mobs))

        # Register brackets
        brackets = mat.get_brackets()
        if len(brackets) >= 2:
            self.register_selector("bracket.left", brackets[0])
            self.register_selector("bracket.right", brackets[1])
