"""Unit tests for LLM Manim source normalization and CodeMode dump salvage."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from manim_source import (  # noqa: E402
    ensure_voiceover_scene,
    extract_codemode_dump,
    normalize_manim_source,
    prepare_manim_source,
)


def test_valid_source_unchanged() -> None:
    src = (
        "from manim import *\n"
        "\n"
        "class MyScene(Scene):\n"
        "    def construct(self):\n"
        "        title = Text('Hi')\n"
        "        self.play(Write(title))\n"
    )
    assert normalize_manim_source(src) == src


def test_collapsed_class_def_and_mixed_indent() -> None:
    raw = '''from manim import *

class BodmasRule(Scene): def construct(self): # Title
title = Text("Understanding the BODMAS Rule", font_size=36)
self.play(Write(title))
self.wait(1)
self.play(FadeOut(title))

text

    # Introduction
    intro_text = Text(
        "BODMAS stands for Bracket, Orders, Division, Multiplication,\\n"
        "Addition, and Subtraction.",
        font_size=28
    )
    self.play(Write(intro_text))
'''
    fixed = normalize_manim_source(raw)
    ast.parse(fixed)
    assert "class BodmasRule(Scene):" in fixed
    assert "def construct(self):" in fixed
    assert "\ntext\n" not in f"\n{fixed}\n"
    assert not any(ln.strip() == "text" for ln in fixed.splitlines())
    tree = ast.parse(fixed)
    class_def = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    construct = class_def.body[0]
    assert isinstance(construct, ast.FunctionDef)
    assert construct.name == "construct"
    assigns = [n for n in construct.body if isinstance(n, ast.Assign)]
    names = [
        t.id
        for a in assigns
        for t in a.targets
        if isinstance(t, ast.Name)
    ]
    assert "title" in names
    assert "intro_text" in names


def test_stray_fence_language_tag_removed() -> None:
    raw = (
        "```python\n"
        "from manim import *\n"
        "\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        self.wait(1)\n"
        "text\n"
        "        self.wait(2)\n"
        "```\n"
    )
    fixed = normalize_manim_source(raw)
    ast.parse(fixed)
    assert "```" not in fixed
    assert not any(ln.strip() == "text" for ln in fixed.splitlines())


def test_escaped_newline_oneliner_becomes_module() -> None:
    raw = (
        'from manim import *\\n\\nclass OrderOfOperations(Scene):\\n'
        '    def construct(self):\\n        title = Text("Hi", font_size=36)\\n'
        "        self.play(Write(title))"
    )
    assert "\n" not in raw
    fixed = normalize_manim_source(raw)
    ast.parse(fixed)
    assert "class OrderOfOperations(Scene):" in fixed
    assert "\n    def construct(self):" in fixed


def test_extract_bodmas_style_codemode_dump() -> None:
    dump = (
        "code = '''from manim import *\\n\\n"
        "class OrderOfOperations(Scene):\\n"
        "    def construct(self):\\n"
        '        title = Text("Order of Operations", font_size=36)\\n'
        "        title.to_edge(UP)\\n"
        "        self.play(Write(title))\\n"
        "        self.wait(1)\\n\\n"
        '        expr = MathTex(r"3 + 4 \\\\times 2", font_size=48)\\n'
        "        expr.next_to(title, DOWN, buff=1)\\n"
        "        self.play(Write(expr))\\n"
        "        self.wait(1)\\n\\n"
        '        conclusion = Text("PEMDAS: Parentheses, Exponents,\\n'
        'Multiplication & Division, Addition & Subtraction", font_size=24)\\n'
        "        self.play(Write(conclusion))\\n"
        "        self.wait(2)'''\n"
        "await manim_write(code=code, scene_name='OrderOfOperations') \n"
        "await compile_manim_code(code=code, scene_name='OrderOfOperations')"
    )
    extracted = extract_codemode_dump(dump)
    assert extracted is not None
    assert extracted.scene_name == "OrderOfOperations"
    ast.parse(extracted.code)
    assert "class OrderOfOperations(Scene):" in extracted.code
    assert "def construct(self):" in extracted.code
    assert "MathTex" in extracted.code


RAW_BODMAS = '''from manim import *

class BODMASRule(Scene):
    def construct(self):
        title = Title("BODMAS Rule")
        self.play(Write(title))
        self.wait(1)

        # Create the expression
        expression = MathTex("5 + 3 \\\\times 4")
        explanation = Text("Evaluate the expression using the BODMAS rule", font_size=24).to_edge(DOWN)

        self.play(Write(expression))
        self.play(FadeIn(explanation))
        self.wait(2)

        # Show BODMAS acronym
        bodmas_acronym = Text("BODMAS", font_size=36)
        bodmas_text = Text("Brackets, Orders, Division, Multiplication, Addition, Subtraction", font_size=24).next_to(bodmas_acronym, DOWN)

        self.play(Transform(expression.copy(), bodmas_acronym), FadeOut(explanation))
        self.play(Write(bodmas_text))
        self.wait(2)

        # Highlight multiplication first
        multiplication_step = MathTex("5 + 12")
        self.play(Transform(expression, multiplication_step))
        self.wait(1)

        # Show final result
        final_result = MathTex("17")
        self.play(Transform(expression, final_result))
        self.wait(2)

        self.clear()
        self.wait(1)

        # Conclusion
        conclusion = Text("Always follow BODMAS for accurate calculations!", font_size=36)
        self.play(Write(conclusion))
        self.wait(2)
'''

VOICEOVER_OK = '''from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService

class IntroScene(VoiceoverScene):
    def construct(self):
        self.set_speech_service(
            AOSSpeechService(voice="alba", cache_dir="voiceover_cache")
        )
        circle = Circle()
        with self.voiceover(text="This circle is drawn as I speak.") as tracker:
            self.play(Create(circle), run_time=tracker.duration)
'''


def test_extract_raw_bodmas_dump() -> None:
    extracted = extract_codemode_dump(RAW_BODMAS)
    assert extracted is not None
    assert extracted.scene_name == "BODMASRule"
    ast.parse(extracted.code)
    assert "class BODMASRule(Scene):" in extracted.code


def test_ensure_voiceover_scene_wraps_plain_scene() -> None:
    wrapped = ensure_voiceover_scene(RAW_BODMAS)
    ast.parse(wrapped)
    assert "class BODMASRule(VoiceoverScene):" in wrapped
    assert "from manim_voiceover import VoiceoverScene" in wrapped
    assert "AOSSpeechService" in wrapped
    assert "set_speech_service" in wrapped
    assert "Let's look at this on the board" not in wrapped
    assert "Here we have" not in wrapped
    tree = ast.parse(wrapped)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert any(
        isinstance(b, ast.Name) and b.id == "VoiceoverScene"
        for cls in classes
        for b in cls.bases
    )
    assert "Watch this next step" not in wrapped
    assert "Always follow BODMAS for accurate calculations" in wrapped


def test_valid_voiceover_scene_unchanged() -> None:
    assert ensure_voiceover_scene(VOICEOVER_OK) == VOICEOVER_OK


def test_silent_plays_not_wrapped_with_filler() -> None:
    src = (
        "from manim import *\n"
        "\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        # Display the problem\n"
        "        problem = MathTex('(a + b)^3').scale(1.5)\n"
        "        self.play(Write(problem))\n"
    )
    wrapped = ensure_voiceover_scene(src)
    assert "Let's look at this on the board" not in wrapped
    assert "Here we have" not in wrapped
    assert "Watch this next step" not in wrapped
    assert "a plus b" not in wrapped.lower()
    assert "self.play(Write(problem))" in wrapped


def test_fadeout_only_play_not_wrapped() -> None:
    src = (
        "from manim import *\n"
        "\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        label = Text('Hello there')\n"
        "        self.play(Write(label))\n"
        "        self.play(FadeOut(label))\n"
    )
    wrapped = ensure_voiceover_scene(src)
    assert "Let's look at this on the board" not in wrapped
    assert "self.play(FadeOut(label))" in wrapped
    assert "Hello there" in wrapped


def test_placeholder_voiceover_not_rewritten_from_text() -> None:
    src = (
        "from manim import *\n"
        "from manim_voiceover import VoiceoverScene\n"
        "from tools.aos_speech_service import AOSSpeechService\n"
        "\n"
        "class Demo(VoiceoverScene):\n"
        "    def construct(self):\n"
        "        self.set_speech_service(\n"
        '            AOSSpeechService(voice="alba", cache_dir="voiceover_cache")\n'
        "        )\n"
        "        with self.voiceover(text='Watch this next step.') as tracker:\n"
        '            self.play(Write(Text("PEMDAS is the order of operations")), '
        "run_time=tracker.duration)\n"
    )
    wrapped = ensure_voiceover_scene(src)
    assert wrapped == src
    assert "Watch this next step" in wrapped


def test_euler_tex_not_copied_into_voiceover() -> None:
    src = (
        "from manim import *\n"
        "\n"
        "class EulersFormulaScene(Scene):\n"
        "    def construct(self):\n"
        '        intro_text = Tex("Let\'s explore the magic of complex numbers.")\n'
        "        self.play(Write(intro_text))\n"
        "        euler_formula = MathTex('e^{ix} = \\\\cos(x) + i\\\\sin(x)').scale(1.5)\n"
        "        self.play(Write(euler_formula))\n"
    )
    wrapped = ensure_voiceover_scene(src)
    assert "Here we have" not in wrapped
    assert "Let's look at this on the board" not in wrapped
    assert "self.play(Write(intro_text))" in wrapped
    assert "self.play(Write(euler_formula))" in wrapped


def test_injects_set_speech_service_when_voiceover_present() -> None:
    src = '''from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService

class DifferenceOfSquares(VoiceoverScene):
    def construct(self):
        title = Text("Difference of Squares Identity")
        self.play(Write(title))
        with self.voiceover(text="The identity factors a squared minus b squared into a plus b times a minus b.") as tracker:
            self.wait(tracker.duration)
'''
    wrapped = ensure_voiceover_scene(src)
    assert "set_speech_service" in wrapped
    assert "AOSSpeechService" in wrapped
    assert "factors a squared minus b squared" in wrapped


BODMAS_ONELINE = (
    "from manim import * class BODMASRule(Scene): def construct(self): "
    'title = Title("BODMAS Rule") self.play(Write(title)) self.wait(1) '
    "# Display the acronym acronyms = VGroup("
    r'Tex("$\\bullet$ Bracket"), Tex("$\\bullet$ Order"), '
    r'Tex("$\\bullet$ Division"), Tex("$\\bullet$ Multiplication"), '
    r'Tex("$\\bullet$ Addition"), Tex("$\\bullet$ Subtraction")) '
    "acronyms.arrange(DOWN, aligned_edge=LEFT, buff=0.5) "
    "self.play(FadeIn(acronyms)) self.wait(2) "
    "# Create a simple equation equation = MathTex("
    r'r"3 + 4 \times 2", r"\rightarrow", r"(3 + 4) \times 2", '
    r'r"\rightarrow", r"7 \times 2", r"\rightarrow", r"14") '
    "equation.scale(1.5) equation.next_to(acronyms, DOWN, buff=1) "
    "self.play(Write(equation[:2])) self.wait(1) "
    "self.play(Transform(equation[0], equation[2])) self.wait(1) "
    "self.play(Transform(equation[0], equation[4])) self.wait(1) "
    "self.play(Transform(equation[0], equation[-1])) self.wait(1) "
    "# Clear the scene self.clear() self.wait(1) "
    "# Show final simplified result final_result = MathTex("
    r'r"3 + 4 \times 2 = 14") '
    "final_result.scale(1.5) self.play(Write(final_result)) self.wait(2) "
)


def test_bodmas_oneline_dump_normalizes() -> None:
    assert "\n" not in BODMAS_ONELINE.strip()
    fixed = normalize_manim_source(BODMAS_ONELINE)
    ast.parse(fixed)
    assert "class BODMASRule" in fixed
    assert "def construct(self):" in fixed
    assert "Write(title)" in fixed
    assert "acronyms" in fixed
    assert "Display the acronym" in fixed
    tree = ast.parse(fixed)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
    assert "acronyms" in names
    assert "final_result" in names
    wrapped = prepare_manim_source(BODMAS_ONELINE)
    ast.parse(wrapped)
    assert "Let's look at this on the board" not in wrapped
    assert "Here we have" not in wrapped
    assert "self.voiceover(" not in wrapped


if __name__ == "__main__":
    tests = [
        test_valid_source_unchanged,
        test_collapsed_class_def_and_mixed_indent,
        test_stray_fence_language_tag_removed,
        test_escaped_newline_oneliner_becomes_module,
        test_extract_bodmas_style_codemode_dump,
        test_extract_raw_bodmas_dump,
        test_ensure_voiceover_scene_wraps_plain_scene,
        test_valid_voiceover_scene_unchanged,
        test_silent_plays_not_wrapped_with_filler,
        test_fadeout_only_play_not_wrapped,
        test_placeholder_voiceover_not_rewritten_from_text,
        test_euler_tex_not_copied_into_voiceover,
        test_injects_set_speech_service_when_voiceover_present,
        test_bodmas_oneline_dump_normalizes,
    ]
    for fn in tests:
        fn()
        print(f"ok {fn.__name__}")
    print("all passed")
