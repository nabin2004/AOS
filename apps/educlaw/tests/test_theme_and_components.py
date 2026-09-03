"""Unit tests for EduClaw theme engine and visual component library."""

from educlaw.animateworkflow.theme import (
    DARK_GLASS,
    SOLARIZED_MATH,
    CLEAN_PASTEL,
    CYBER_NEON,
    get_theme,
    list_themes,
    EduClawTheme,
    ColorPalette,
)
from educlaw.animateworkflow.components import (
    get_component_gallery,
    get_components_prompt_injection,
    COMPONENT_REGISTRY,
)


def test_theme_registry():
    themes = list_themes()
    assert "dark_glass" in themes
    assert "solarized_math" in themes
    assert "clean_pastel" in themes
    assert "cyber_neon" in themes


def test_get_theme_default():
    theme = get_theme()
    assert theme.name == "dark_glass"
    assert theme.palette.background == "#0F1117"


def test_get_theme_specific():
    theme = get_theme("solarized-math")
    assert theme.name == "solarized_math"
    assert theme.palette.background == "#002B36"


def test_theme_to_manim_constants():
    constants_code = DARK_GLASS.to_manim_constants()
    assert 'BG_COLOR = "#0F1117"' in constants_code
    assert 'PRIMARY_COLOR = "#58C4DD"' in constants_code
    assert 'FONT_FAMILY = "Sans-Serif"' in constants_code


def test_custom_theme():
    palette = ColorPalette(name="custom", background="#111111", primary="#FF0000")
    theme = EduClawTheme(name="custom", palette=palette)
    code = theme.to_manim_constants()
    assert 'BG_COLOR = "#111111"' in code
    assert 'PRIMARY_COLOR = "#FF0000"' in code


def test_component_gallery():
    gallery = get_component_gallery()
    assert len(gallery) >= 4
    names = [c.name for c in gallery]
    assert "MathCalloutCard" in names
    assert "ProofContainer" in names
    assert "CodeWindow" in names


def test_components_prompt_injection():
    injection = get_components_prompt_injection()
    assert "MathCalloutCard" in injection
    assert "def create_math_callout" in injection
    assert "def create_proof_step" in injection
