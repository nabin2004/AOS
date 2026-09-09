"""Tests for coordinate sanitization in tools.manim_source."""

from tools.manim_source import sanitize_manim_animations


def test_sanitizes_uniform_size_two() -> None:
    code = """
pos = np.random.uniform(-3, 3, 2)
charge = Dot(point=pos, color=WHITE, radius=0.15)
"""
    sanitized = sanitize_manim_animations(code)
    assert "np.random.uniform(-3, 3, 3)" in sanitized
    assert "np.random.uniform(-3, 3, 2)" not in sanitized


def test_sanitizes_rand_randn_size_two() -> None:
    code = """
p1 = np.random.rand(2)
p2 = np.random.randn(2)
"""
    sanitized = sanitize_manim_animations(code)
    assert "np.random.rand(3)" in sanitized
    assert "np.random.randn(3)" in sanitized


def test_sanitizes_dot_line_arrow_2d_literals() -> None:
    code = """
d = Dot(point=[1.0, 2.0])
l = Line(start=[0, 0], end=[1, 2])
a = Arrow(start=(1, 1), end=(3, 3))
"""
    sanitized = sanitize_manim_animations(code)
    assert "Dot(point=[1.0, 2.0, 0])" in sanitized
    assert "Line(start=[0, 0, 0], end=[1, 2, 0])" in sanitized
    assert "Arrow(start=(1, 1, 0), end=(3, 3, 0))" in sanitized
