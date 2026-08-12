"""Board color themes for 2D chess boards (aligned with chess.svg color keys)."""

from __future__ import annotations

from dataclasses import dataclass

from manim import BLUE_E, GREEN_E, GREY_B, RED_E, YELLOW


@dataclass(frozen=True)
class BoardTheme:
    """Visual theme for 2D chess boards."""

    # Match chess.svg defaults where practical
    light_square: str = "#ffce9e"  # square light
    dark_square: str = "#d18b47"  # square dark
    highlight: str = YELLOW
    lastmove_light: str = "#cdd16a"
    lastmove_dark: str = "#aaa23b"
    arrow: str = GREEN_E
    legal_move: str = BLUE_E
    capture_hint: str = RED_E
    attack_fill: str = "#cc000088"
    label: str = GREY_B
    square_stroke_width: float = 0.5
    # Fraction of square side used for SVG piece glyph
    piece_fill: float = 0.82

    @classmethod
    def classic(cls) -> BoardTheme:
        return cls()

    @classmethod
    def green(cls) -> BoardTheme:
        return cls(light_square="#E8EEDF", dark_square="#769656")

    @classmethod
    def blue(cls) -> BoardTheme:
        return cls(light_square="#DEE3E6", dark_square="#8CA2AD")

    def svg_colors(self) -> dict[str, str]:
        """Color dict compatible with chess.svg.board(..., colors=...)."""
        return {
            "square light": self.light_square,
            "square dark": self.dark_square,
            "square light lastmove": self.lastmove_light,
            "square dark lastmove": self.lastmove_dark,
            "coord": self.label if isinstance(self.label, str) else "#888888",
        }
