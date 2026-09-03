"""Unit tests for Manim API Knowledge Base."""

from educlaw.animateworkflow.manim_kb import (
    lookup_manim_symbol,
    search_manim_symbols,
    MANIM_KB,
)


def test_lookup_exact_symbol():
    doc = lookup_manim_symbol("MathTex")
    assert doc is not None
    assert doc.name == "MathTex"
    assert doc.symbol_type == "class"
    assert "LaTeX" in doc.description


def test_lookup_case_insensitive():
    doc = lookup_manim_symbol("mathtex")
    assert doc is not None
    assert doc.name == "MathTex"


def test_lookup_animation():
    doc = lookup_manim_symbol("Create")
    assert doc is not None
    assert doc.symbol_type == "animation"
    assert "run_time" in doc.valid_kwargs


def test_search_manim_symbols():
    results = search_manim_symbols("transform")
    assert len(results) >= 2
    names = [r.name for r in results]
    assert "Transform" in names
    assert "ReplacementTransform" in names


def test_lookup_voiceover_scene():
    doc = lookup_manim_symbol("VoiceoverScene")
    assert doc is not None
    assert any("context manager" in pitfall for pitfall in doc.common_pitfalls)
