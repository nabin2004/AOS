"""Pedagogical Visual Design & Theme System for Manim scenes."""

from __future__ import annotations

from typing import Dict
from pydantic import BaseModel, Field


class ColorPalette(BaseModel):
    """Color palette specifications for mathematical and visual elements."""

    name: str = Field(description="Unique identifier for the color palette")
    background: str = Field(default="#0F1117", description="Background hex color")
    primary: str = Field(default="#58C4DD", description="Primary accent / main object color")
    secondary: str = Field(default="#83C167", description="Secondary accent color")
    accent: str = Field(default="#FFFF00", description="Highlight or alert color")
    text: str = Field(default="#ECEFF4", description="Base readable text color")
    math: str = Field(default="#FFF176", description="Formula and LaTeX color")
    subtext: str = Field(default="#88C0D0", description="Muted description or label color")


class EduClawTheme(BaseModel):
    """Complete declarative theme encapsulating palette, typography, and syntax highlighting."""

    name: str = Field(default="dark_glass", description="Theme name")
    palette: ColorPalette = Field(description="Associated color palette")
    font: str = Field(default="Sans-Serif", description="Primary typography font family")
    code_theme: str = Field(default="monokai", description="Syntax highlighting theme for code")

    def to_manim_constants(self) -> str:
        """Convert theme colors into executable Python constant assignments for Manim scenes."""
        p = self.palette
        return (
            f"# EduClaw Theme: {self.name}\n"
            f'BG_COLOR = "{p.background}"\n'
            f'PRIMARY_COLOR = "{p.primary}"\n'
            f'SECONDARY_COLOR = "{p.secondary}"\n'
            f'ACCENT_COLOR = "{p.accent}"\n'
            f'TEXT_COLOR = "{p.text}"\n'
            f'MATH_COLOR = "{p.math}"\n'
            f'SUBTEXT_COLOR = "{p.subtext}"\n'
            f'FONT_FAMILY = "{self.font}"\n'
        )


DARK_GLASS = EduClawTheme(
    name="dark_glass",
    palette=ColorPalette(
        name="dark_glass",
        background="#0F1117",
        primary="#58C4DD",
        secondary="#83C167",
        accent="#FC6255",
        text="#ECEFF4",
        math="#FFF176",
        subtext="#88C0D0",
    ),
    font="Sans-Serif",
    code_theme="monokai",
)

SOLARIZED_MATH = EduClawTheme(
    name="solarized_math",
    palette=ColorPalette(
        name="solarized_math",
        background="#002B36",
        primary="#268BD2",
        secondary="#2AA198",
        accent="#D33682",
        text="#93A1A1",
        math="#B58900",
        subtext="#657B83",
    ),
    font="Serif",
    code_theme="solarized-dark",
)

CLEAN_PASTEL = EduClawTheme(
    name="clean_pastel",
    palette=ColorPalette(
        name="clean_pastel",
        background="#1E1E2E",
        primary="#89B4FA",
        secondary="#A6E3A1",
        accent="#F38BA8",
        text="#CDD6F4",
        math="#F9E2AF",
        subtext="#BAC2DE",
    ),
    font="Sans-Serif",
    code_theme="catppuccin-mocha",
)

CYBER_NEON = EduClawTheme(
    name="cyber_neon",
    palette=ColorPalette(
        name="cyber_neon",
        background="#0A0A12",
        primary="#00F0FF",
        secondary="#39FF14",
        accent="#FF007F",
        text="#F0F0FF",
        math="#FFE600",
        subtext="#7928CA",
    ),
    font="Monospace",
    code_theme="dracula",
)

THEME_REGISTRY: Dict[str, EduClawTheme] = {
    "dark_glass": DARK_GLASS,
    "solarized_math": SOLARIZED_MATH,
    "clean_pastel": CLEAN_PASTEL,
    "cyber_neon": CYBER_NEON,
}


def get_theme(name: str | None = None) -> EduClawTheme:
    """Retrieve an EduClaw theme by name, defaulting to dark_glass."""
    if not name:
        return DARK_GLASS
    normalized = name.strip().lower().replace("-", "_")
    return THEME_REGISTRY.get(normalized, DARK_GLASS)


def list_themes() -> list[str]:
    """Return a list of available theme names."""
    return list(THEME_REGISTRY.keys())
