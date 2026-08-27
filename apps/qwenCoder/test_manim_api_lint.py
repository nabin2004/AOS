from __future__ import annotations

import pytest

from manim_api_lint import is_coverage_rich, is_lint_clean, lint_source


def test_valid_axes_snippet_passes() -> None:
    src = """
from manim import *

class Demo(Scene):
    def construct(self):
        axes = Axes(x_range=[-1, 1, 1], y_range=[-1, 1, 1])
        self.play(Create(axes))
"""
    assert is_lint_clean(src)


def test_matrix_element_color_banned() -> None:
    src = """
from manim import *

class Demo(Scene):
    def construct(self):
        m = Matrix([[1, 0], [0, 1]], element_color=RED)
        self.add(m)
"""
    issues = lint_source(src)
    assert any(i.code == "banned_kwarg" and "element_color" in i.message for i in issues)


def test_numberline_max_value_banned() -> None:
    src = """
from manim import *

class Demo(Scene):
    def construct(self):
        n = NumberLine(max_value=10)
        self.add(n)
"""
    issues = lint_source(src)
    assert any(i.code == "banned_kwarg" and "max_value" in i.message for i in issues)


def test_arrow_vector_field_max_magnitude_banned() -> None:
    src = """
from manim import *
import numpy as np

class Demo(Scene):
    def construct(self):
        field = ArrowVectorField(lambda p: p, max_magnitude=2)
        self.add(field)
"""
    issues = lint_source(src)
    assert any(i.code == "banned_kwarg" and "max_magnitude" in i.message for i in issues)


def test_unicode_subscript_in_mathtex() -> None:
    src = """
from manim import *

class Demo(Scene):
    def construct(self):
        t = MathTex("w\u2081")
        self.add(t)
"""
    issues = lint_source(src)
    assert any(i.code == "unicode_tex" for i in issues)


def test_mathtex_latex_subscript_ok() -> None:
    src = """
from manim import *

class Demo(Scene):
    def construct(self):
        t = MathTex(r"w_1")
        self.add(t)
"""
    assert is_lint_clean(src)


def test_vgroup_c2p_rejected() -> None:
    src = """
from manim import *

class Demo(Scene):
    def construct(self):
        x_axis = NumberLine()
        y_axis = NumberLine()
        axes_group = VGroup(x_axis, y_axis)
        p = axes_group.c2p(1, 0)
        self.add(Dot(p))
"""
    issues = lint_source(src)
    assert any(i.code == "c2p" for i in issues)


def test_axes_c2p_ok() -> None:
    src = """
from manim import *

class Demo(Scene):
    def construct(self):
        axes = Axes()
        p = axes.c2p(1, 0)
        self.add(Dot(p))
"""
    assert is_lint_clean(src)


def test_showcreation_banned() -> None:
    src = """
from manim import *

class Demo(Scene):
    def construct(self):
        self.play(ShowCreation(Circle()))
"""
    issues = lint_source(src)
    assert any(i.code == "banned_name" for i in issues)


def test_mro_unknown_kwarg_when_manim_installed() -> None:
    pytest.importorskip("manim")
    src = """
from manim import *

class Demo(Scene):
    def construct(self):
        c = Circle(not_a_real_kwarg=1)
        self.add(c)
"""
    issues = lint_source(src)
    assert any(i.code == "unknown_kwarg" for i in issues)


def test_coverage_rich() -> None:
    src = """
self.play(LaggedStart(FadeIn(a), FadeIn(b)))
self.play(Transform(a, b), Transform(c, d))
self.play(FadeOut(a), FadeOut(b))
"""
    assert is_coverage_rich(src)
