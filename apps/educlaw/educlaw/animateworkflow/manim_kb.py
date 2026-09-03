"""Manim Community Edition API Knowledge Base & Symbol Documentation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ManimSymbolDoc(BaseModel):
    """Document model representing verified ManimCE API signatures and rules."""

    name: str = Field(description="Name of the class, method, or animation")
    symbol_type: str = Field(description="Type: class, animation, transform, or utility")
    signature: str = Field(description="Exact Python invocation signature")
    description: str = Field(description="Summary of purpose and visual effect")
    valid_kwargs: List[str] = Field(default_factory=list, description="Supported keyword arguments")
    common_pitfalls: List[str] = Field(default_factory=list, description="Common anti-patterns or hallucinations")
    example_usage: str = Field(default="", description="Clean example snippet")


# Built-in curated ManimCE API Knowledge Base
MANIM_KB: Dict[str, ManimSymbolDoc] = {
    "MathTex": ManimSymbolDoc(
        name="MathTex",
        symbol_type="class",
        signature="MathTex(*tex_strings, font_size=48, color=WHITE, **kwargs)",
        description="Renders mathematical formulas and expressions using LaTeX math mode.",
        valid_kwargs=["font_size", "color", "tex_environment", "substrings_to_isolate", "arg_separator"],
        common_pitfalls=[
            "Do not pass plain text without LaTeX escaping (e.g. use \\\\ for linebreaks).",
            "Use raw strings r'...' for backslash expressions like r'\\frac{a}{b}'.",
        ],
        example_usage="eq = MathTex(r'E = mc^2', font_size=36, color=YELLOW)",
    ),
    "Text": ManimSymbolDoc(
        name="Text",
        symbol_type="class",
        signature="Text(text, font_size=48, color=WHITE, font='', weight='NORMAL', **kwargs)",
        description="Renders standard typography using system fonts via Pango.",
        valid_kwargs=["font_size", "color", "font", "weight", "slant", "gradient", "line_spacing"],
        common_pitfalls=[
            "Do not use LaTeX math commands in Text; use MathTex for math.",
            "Text objects do not support tex_environment.",
        ],
        example_usage="title = Text('Pythagorean Theorem', font_size=32, weight=BOLD)",
    ),
    "Create": ManimSymbolDoc(
        name="Create",
        symbol_type="animation",
        signature="Create(mobject, run_time=1.0, rate_func=smooth, **kwargs)",
        description="Draws a VMobject on screen from start to finish.",
        valid_kwargs=["run_time", "rate_func", "lag_ratio", "introducer"],
        common_pitfalls=[
            "Passing an already created object without FadeOut or replacement causes visual glitches.",
        ],
        example_usage="self.play(Create(circle), run_time=1.5)",
    ),
    "Write": ManimSymbolDoc(
        name="Write",
        symbol_type="animation",
        signature="Write(vmobject, run_time=1.0, rate_func=linear, reverse=False, **kwargs)",
        description="Simulates writing or typing out text, mathematical formulas, or shapes.",
        valid_kwargs=["run_time", "rate_func", "reverse", "lag_ratio"],
        common_pitfalls=["Best suited for Text and MathTex, not filled geometries."],
        example_usage="self.play(Write(formula))",
    ),
    "Transform": ManimSymbolDoc(
        name="Transform",
        symbol_type="transform",
        signature="Transform(mobject, target_mobject, path_arc=0.0, **kwargs)",
        description="Morphs one mobject into another mobject in place.",
        valid_kwargs=["path_arc", "run_time", "rate_func", "replace_mobject_with_target_in_scene"],
        common_pitfalls=[
            "Transform modifies the original mobject in-place. If you want replacement, use ReplacementTransform.",
        ],
        example_usage="self.play(Transform(rect, circle))",
    ),
    "ReplacementTransform": ManimSymbolDoc(
        name="ReplacementTransform",
        symbol_type="transform",
        signature="ReplacementTransform(mobject, target_mobject, **kwargs)",
        description="Morphs mobject into target_mobject and replaces it in the scene hierarchy.",
        valid_kwargs=["path_arc", "run_time", "rate_func"],
        common_pitfalls=["Do not reference the old mobject after a ReplacementTransform."],
        example_usage="self.play(ReplacementTransform(step1, step2))",
    ),
    "SurroundingRectangle": ManimSymbolDoc(
        name="SurroundingRectangle",
        symbol_type="class",
        signature="SurroundingRectangle(mobject, color=YELLOW, buff=0.1, corner_radius=0.0, **kwargs)",
        description="Creates a bounding box container surrounding a target mobject.",
        valid_kwargs=["color", "buff", "corner_radius", "stroke_width", "fill_opacity", "fill_color"],
        common_pitfalls=["Remember to animate or add the surrounding box to the scene with Create/FadeIn."],
        example_usage="box = SurroundingRectangle(eq, color=PRIMARY_COLOR, buff=0.2)",
    ),
    "NumberLine": ManimSymbolDoc(
        name="NumberLine",
        symbol_type="class",
        signature="NumberLine(x_range=[x_min, x_max, step], length=None, include_numbers=False, **kwargs)",
        description="Renders a 1D real number line with ticks and numerical labels.",
        valid_kwargs=["x_range", "length", "include_numbers", "color", "font_size", "line_to_number_buff"],
        common_pitfalls=["x_range must be a 3-element list or tuple: [min, max, step]."],
        example_usage="axis = NumberLine(x_range=[-5, 5, 1], length=10, include_numbers=True)",
    ),
    "Axes": ManimSymbolDoc(
        name="Axes",
        symbol_type="class",
        signature="Axes(x_range=None, y_range=None, x_length=None, y_length=None, tips=True, **kwargs)",
        description="2D coordinate frame composed of perpendicular x and y number lines.",
        valid_kwargs=["x_range", "y_range", "x_length", "y_length", "axis_config", "tips"],
        common_pitfalls=["Coordinates must be plotted using axes.c2p(x, y) or axes.plot(...)."],
        example_usage="axes = Axes(x_range=[-3, 3, 1], y_range=[-2, 2, 1], x_length=6, y_length=4)",
    ),
    "VoiceoverScene": ManimSymbolDoc(
        name="VoiceoverScene",
        symbol_type="class",
        signature="VoiceoverScene",
        description="Manim Scene subclass providing self.voiceover(text=...) context manager.",
        valid_kwargs=[],
        common_pitfalls=[
            "Never pass Voiceover into self.play(). Always use it as a context manager: 'with self.voiceover(...) as tracker:'.",
            "Do not invent speech service classes not installed in the Docker image.",
        ],
        example_usage="class MyScene(VoiceoverScene):\n    def construct(self):\n        with self.voiceover(text='Hello') as tracker:\n            self.play(Create(dot))",
    ),
}


def lookup_manim_symbol(name: str) -> Optional[ManimSymbolDoc]:
    """Look up symbol by exact name, normalized case-insensitive, or best prefix match."""
    normalized = name.strip()
    if normalized in MANIM_KB:
        return MANIM_KB[normalized]

    lower_map = {k.lower(): v for k, v in MANIM_KB.items()}
    if normalized.lower() in lower_map:
        return lower_map[normalized.lower()]

    # Substring search
    for k, doc in MANIM_KB.items():
        if normalized.lower() in k.lower():
            return doc
    return None


def search_manim_symbols(query: str, limit: int = 5) -> List[ManimSymbolDoc]:
    """Search knowledge base symbols by query string."""
    q = query.strip().lower()
    matches: List[ManimSymbolDoc] = []
    for k, doc in MANIM_KB.items():
        if q in k.lower() or q in doc.description.lower():
            matches.append(doc)
            if len(matches) >= limit:
                break
    return matches
