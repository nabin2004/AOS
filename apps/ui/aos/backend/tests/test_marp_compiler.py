"""Unit tests for MarpManimCompiler — deterministic AST parser and layout compiler."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.services.marp_compiler import MarpCompilerResult, MarpManimCompiler, MarpParser, MarpSlide


SAMPLE_MARP_DECK = r"""---
marp: true
theme: default
voiceover: "Welcome to this lecture on neural optimization."
---

<!-- _class: title -->
# Deep Learning Optimization
### From Gradient Descent to Adam

---
<!-- _class: bullets -->
## Core Fundamentals
- High-dimensional parameter landscape
- Negative gradient direction
- Learning rate scaling

---
<!-- _class: two-col -->
## SGD vs Batch Gradient Descent
- Faster iteration updates
- High variance noisy path

- Deterministic exact gradients
- High GPU memory overhead

---
<!-- _class: code-focus -->
## PyTorch Optimizer Step
```python
optimizer.zero_grad()
loss.backward()
optimizer.step()
```

---
<!-- _class: math-focus -->
## The Weight Update Equation
$$ w_{t+1} = w_t - \eta \nabla L(w_t) $$
- $\eta$ represents the learning rate
- $\nabla L$ is the gradient vector

---
<!-- _class: quote -->
> "Study what interests you in the most undisciplined, irreverent manner."
— Richard Feynman
"""


def test_marp_parser_slide_extraction():
    """Verify that MarpParser extracts all 6 slide archetypes with their respective models."""
    parser = MarpParser()
    slides = parser.parse(SAMPLE_MARP_DECK)

    assert len(slides) == 6

    # Slide 1: Title
    s1 = slides[0]
    assert s1.layout == "title"
    assert s1.title == "Deep Learning Optimization"
    assert s1.subtitle == "From Gradient Descent to Adam"
    assert s1.voiceover == "Welcome to this lecture on neural optimization."

    # Slide 2: Bullets
    s2 = slides[1]
    assert s2.layout == "bullets"
    assert s2.title == "Core Fundamentals"
    assert len(s2.bullets) == 3
    assert "High-dimensional parameter landscape" in s2.bullets[0]

    # Slide 3: Two-col
    s3 = slides[2]
    assert s3.layout == "two-col"
    assert s3.title == "SGD vs Batch Gradient Descent"
    assert len(s3.col1_items) > 0
    assert len(s3.col2_items) > 0

    # Slide 4: Code-focus
    s4 = slides[3]
    assert s4.layout == "code-focus"
    assert s4.code is not None
    assert "optimizer.step()" in s4.code
    assert s4.code_lang == "python"

    # Slide 5: Math-focus
    s5 = slides[4]
    assert s5.layout == "math-focus"
    assert len(s5.math_equations) > 0
    assert "w_{t+1}" in s5.math_equations[0]

    # Slide 6: Quote
    s6 = slides[5]
    assert s6.layout == "quote"
    assert s6.quote_text is not None
    assert "irreverent" in s6.quote_text
    assert s6.quote_author == "Richard Feynman"


def test_marp_compiler_emits_valid_python_ast():
    """Verify that emitted Manim code parses cleanly as valid Python AST without syntax errors."""
    compiler = MarpManimCompiler()
    res = compiler.compile(SAMPLE_MARP_DECK, scene_name="OptimizationLectureScene", target="video")

    assert isinstance(res, MarpCompilerResult)
    assert res.slide_count == 6
    assert res.scene_name == "OptimizationLectureScene"
    assert res.target == "video"

    # AST Syntax verification
    parsed_ast = ast.parse(res.code)
    assert parsed_ast is not None

    # Structural checks
    code = res.code
    assert "from manim import *" in code
    assert "class OptimizationLectureScene(Scene):" in code
    assert "def construct(self):" in code
    assert "BulletedList" in code
    assert "Code(" in code
    assert "MathTex(" in code
    assert "VGroup" in code
    assert "self.wait(2.5)" in code


def test_marp_compiler_slides_target():
    """Verify that compiling with target='slides' uses manim_slides import and Slide base class."""
    compiler = MarpManimCompiler()
    res = compiler.compile(SAMPLE_MARP_DECK, scene_name="DeckScene", target="slides")

    assert "from manim_slides import Slide" in res.code
    assert "class DeckScene(Slide):" in code_sample if "code_sample" in locals() else "class DeckScene(Slide):" in res.code
    assert "self.next_slide()" in res.code


def test_marp_compiler_empty_fallback():
    """Verify that empty or minimal text produces a safe fallback scene."""
    compiler = MarpManimCompiler()
    res = compiler.compile("", scene_name="EmptyScene")

    assert res.slide_count >= 1
    parsed_ast = ast.parse(res.code)
    assert parsed_ast is not None
