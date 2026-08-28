from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
from manim.utils.color import ManimColor


@dataclass
class SemanticPalette:
    """Semantic color palette providing theme-agnostic tokens."""
    primary: str = "#3B82F6"           # Blue 500
    secondary: str = "#8B5CF6"         # Purple 500
    accent: str = "#EC4899"            # Pink 500
    accent_secondary: str = "#10B981"  # Emerald 500
    background: str = "#0B0F19"        # Deep midnight
    surface: str = "#1E293B"           # Slate 800
    surface_variant: str = "#334155"   # Slate 700
    border: str = "#475569"            # Slate 600
    text_main: str = "#F8FAFC"         # Slate 50
    text_muted: str = "#94A3B8"        # Slate 400
    success: str = "#10B981"           # Green 500
    warning: str = "#F59E0B"           # Amber 500
    error: str = "#EF4444"             # Red 500
    highlight_a: str = "#FACC15"       # Yellow 400
    highlight_b: str = "#06B6D4"       # Cyan 500
    node_color: str = "#3B82F6"
    edge_color: str = "#64748B"

    def get_color(self, name: str, default: Optional[str] = None) -> ManimColor:
        """Retrieve color token as a ManimColor."""
        hex_val = getattr(self, name, default or self.primary)
        return ManimColor(hex_val)

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SemanticPalette:
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: str(v) for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


@dataclass
class FontConfig:
    """Typography configuration for consistent presentation across plugins."""
    text_font: str = ""
    code_font: str = "Monospace"
    title_font_size: int = 40
    heading_font_size: int = 32
    body_font_size: int = 24
    code_font_size: int = 20
    caption_font_size: int = 16

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FontConfig:
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


@dataclass
class ThemeConfig:
    """Global or scoped theme configuration."""
    name: str = "default_dark"
    is_dark: bool = True
    palette: SemanticPalette = field(default_factory=SemanticPalette)
    fonts: FontConfig = field(default_factory=FontConfig)
    canvas_margin: float = 0.6
    default_stroke_width: float = 3.0
    corner_radius: float = 0.15

    # Convenient color accessors
    @property
    def primary(self) -> ManimColor:
        return self.palette.get_color("primary")

    @property
    def secondary(self) -> ManimColor:
        return self.palette.get_color("secondary")

    @property
    def accent(self) -> ManimColor:
        return self.palette.get_color("accent")

    @property
    def accent_secondary(self) -> ManimColor:
        return self.palette.get_color("accent_secondary")

    @property
    def background(self) -> ManimColor:
        return self.palette.get_color("background")

    @property
    def surface(self) -> ManimColor:
        return self.palette.get_color("surface")

    @property
    def surface_variant(self) -> ManimColor:
        return self.palette.get_color("surface_variant")

    @property
    def border(self) -> ManimColor:
        return self.palette.get_color("border")

    @property
    def text_main(self) -> ManimColor:
        return self.palette.get_color("text_main")

    @property
    def text_muted(self) -> ManimColor:
        return self.palette.get_color("text_muted")

    @property
    def success(self) -> ManimColor:
        return self.palette.get_color("success")

    @property
    def warning(self) -> ManimColor:
        return self.palette.get_color("warning")

    @property
    def error(self) -> ManimColor:
        return self.palette.get_color("error")

    @property
    def highlight_a(self) -> ManimColor:
        return self.palette.get_color("highlight_a")

    @property
    def highlight_b(self) -> ManimColor:
        return self.palette.get_color("highlight_b")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "is_dark": self.is_dark,
            "palette": self.palette.to_dict(),
            "fonts": self.fonts.to_dict(),
            "canvas_margin": self.canvas_margin,
            "default_stroke_width": self.default_stroke_width,
            "corner_radius": self.corner_radius,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ThemeConfig:
        palette_data = data.get("palette", {})
        fonts_data = data.get("fonts", {})
        return cls(
            name=data.get("name", "custom"),
            is_dark=data.get("is_dark", True),
            palette=SemanticPalette.from_dict(palette_data),
            fonts=FontConfig.from_dict(fonts_data),
            canvas_margin=data.get("canvas_margin", 0.6),
            default_stroke_width=data.get("default_stroke_width", 3.0),
            corner_radius=data.get("corner_radius", 0.15),
        )
