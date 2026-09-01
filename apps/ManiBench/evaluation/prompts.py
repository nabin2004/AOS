"""
ManiBench Evaluation — Prompt Strategies
==========================================
Implements the prompting approaches from ManiBench_Prompt_Engineering_Guide.md:
  1. Zero-shot direct
  2. Few-shot with examples
  3. Chain-of-thought (CoT)
  4. Constraint-based (explicit timing/ordering)
  5. Version-conflict-aware

Each strategy takes a problem dict and returns a list of chat messages.
"""

from typing import Any


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

SYSTEM_BASE = (
    "You are a Manim animation expert. You write clean, correct, "
    "executable Manim CE (Community Edition) code. "
    "Target: `pip install manim` (Community Edition). "
    "Do NOT use ManimGL, manim_imports_ext, or 3Blue1Brown's personal fork. "
    "Output ONLY valid Python code."
)

SYSTEM_VERSION_AWARE = (
    "You are a Manim CE (Community Edition) expert. "
    "You write code strictly compatible with `pip install manim` (CE).\n\n"
    "FORBIDDEN constructs (ManimGL-only, will cause errors in CE):\n"
    "- CONFIG class dictionaries → use __init__ parameters\n"
    "- ShowCreation() → use Create()\n"
    "- FadeInFrom(m, LEFT) → use FadeIn(m, shift=LEFT)\n"
    "- GraphScene → use Axes object\n"
    "- InteractiveScene, ReconfigurableScene → use Scene\n"
    "- TeacherStudentsScene, PiCreature, Eyes → not available\n"
    "- self.frame → use self.camera.frame (MovingCameraScene)\n"
    "- OldTex, OldTexText, TexMobject, TextMobject → use Tex, MathTex, Text\n"
    "- apply_depth_test(), set_shading() → OpenGL renderer only\n"
    "- force_skipping → not available\n"
    "- GlowDot, DieFace, TrueDot → not available\n\n"
    "Output ONLY valid Python code. No explanations."
)


# ---------------------------------------------------------------------------
# Strategy builders
# ---------------------------------------------------------------------------

def build_messages(
    problem: dict[str, Any],
    strategy: str = "zero_shot",
) -> list[dict[str, str]]:
    """
    Build chat messages for a given problem and prompting strategy.

    Args:
        problem: A problem dict from ManiBench_Pilot_Dataset.json
        strategy: One of 'zero_shot', 'few_shot', 'cot', 'constraint', 'version_aware'

    Returns:
        List of {"role": ..., "content": ...} message dicts
    """
    builders = {
        "zero_shot": _zero_shot,
        "few_shot": _few_shot,
        "cot": _cot,
        "constraint": _constraint,
        "version_aware": _version_aware,
    }
    builder = builders.get(strategy)
    if not builder:
        raise ValueError(f"Unknown strategy: {strategy}. Choose from {list(builders)}")
    return builder(problem)


# ---------------------------------------------------------------------------
# 1. Zero-shot
# ---------------------------------------------------------------------------

def _zero_shot(problem: dict) -> list[dict[str, str]]:
    prompt = problem["full_prompt"]
    return [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": (
            f"Write Manim CE code to create the following animation:\n\n"
            f"{prompt}\n\n"
            f"Requirements:\n"
            f"- Target Manim Community Edition (CE), not ManimGL\n"
            f"- Ensure code is syntactically valid and executable\n"
            f"- All visual elements should be labeled clearly\n"
            f"- Use `from manim import *`\n\n"
            f"Output ONLY the Python code."
        )},
    ]


# ---------------------------------------------------------------------------
# 2. Few-shot
# ---------------------------------------------------------------------------

FEW_SHOT_EXAMPLE_1 = '''
from manim import *

class CircleToSquare(Scene):
    def construct(self):
        circle = Circle(color=BLUE, fill_opacity=0.5)
        square = Square(color=RED, fill_opacity=0.5)
        label = Text("Transform", font_size=24).to_edge(UP)

        self.play(Create(circle), Write(label))
        self.wait(0.5)
        self.play(Transform(circle, square), run_time=2)
        self.wait(1)
'''.strip()

FEW_SHOT_EXAMPLE_2 = '''
from manim import *

class GradientDescentSimple(Scene):
    def construct(self):
        axes = Axes(x_range=[-3, 3], y_range=[0, 10], axis_config={"include_numbers": True})
        labels = axes.get_axis_labels(x_label="w", y_label="L(w)")
        curve = axes.plot(lambda x: x**2 + 1, color=BLUE)

        dot = Dot(axes.c2p(-2.5, (-2.5)**2 + 1), color=RED)
        loss_label = MathTex("L(w) = w^2 + 1").to_corner(UR)

        self.play(Create(axes), Write(labels), Create(curve), Write(loss_label))
        self.play(FadeIn(dot))
        self.wait(0.5)

        # Gradient descent steps
        w = -2.5
        lr = 0.3
        for step in range(6):
            grad = 2 * w
            w_new = w - lr * grad
            new_pos = axes.c2p(w_new, w_new**2 + 1)
            arrow = Arrow(dot.get_center(), new_pos, buff=0.1, color=YELLOW)
            step_text = Text(f"Step {step+1}", font_size=20).to_edge(DOWN)

            self.play(Create(arrow), Write(step_text), run_time=0.5)
            self.play(dot.animate.move_to(new_pos), run_time=0.5)
            self.play(FadeOut(arrow), FadeOut(step_text), run_time=0.3)
            w = w_new
            lr *= 0.9

        final = Text("Converged!", font_size=28, color=GREEN).next_to(dot, UP)
        self.play(Write(final))
        self.wait(1)
'''.strip()


def _few_shot(problem: dict) -> list[dict[str, str]]:
    prompt = problem["full_prompt"]
    return [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": "Write Manim CE code for a circle-to-square transformation with a label."},
        {"role": "assistant", "content": f"```python\n{FEW_SHOT_EXAMPLE_1}\n```"},
        {"role": "user", "content": "Write Manim CE code for simple 1D gradient descent with step counter."},
        {"role": "assistant", "content": f"```python\n{FEW_SHOT_EXAMPLE_2}\n```"},
        {"role": "user", "content": (
            f"Great. Now write Manim CE code for the following problem:\n\n"
            f"{prompt}\n\n"
            f"Follow the same style: clean code, clear labels, smooth animations. "
            f"Use `from manim import *`. Output ONLY the Python code."
        )},
    ]


# ---------------------------------------------------------------------------
# 3. Chain-of-Thought
# ---------------------------------------------------------------------------

def _cot(problem: dict) -> list[dict[str, str]]:
    prompt = problem["full_prompt"]
    events = problem.get("required_visual_events", [])
    events_text = "\n".join(
        f"  {i+1}. {e['description']} (weight={e['weight']})"
        for i, e in enumerate(events)
    )
    return [
        {"role": "system", "content": SYSTEM_VERSION_AWARE},
        {"role": "user", "content": (
            f"Solve this animation problem step-by-step.\n\n"
            f"PROBLEM:\n{prompt}\n\n"
            f"REQUIRED VISUAL EVENTS:\n{events_text}\n\n"
            f"Before writing code, analyze:\n"
            f"1. What are the main visual components (mobjects)?\n"
            f"2. In what order should events appear?\n"
            f"3. What transformations and animations are needed?\n"
            f"4. How should timing be synchronized?\n"
            f"5. What labels, formulas, and numeric values must be displayed?\n\n"
            f"Then write clean, complete Manim CE code. "
            f"Use `from manim import *`. Output the analysis briefly, then the full code."
        )},
    ]


# ---------------------------------------------------------------------------
# 4. Constraint-based
# ---------------------------------------------------------------------------

def _constraint(problem: dict) -> list[dict[str, str]]:
    prompt = problem["full_prompt"]
    events = problem.get("required_visual_events", [])
    coverage = problem.get("coverage_requirements", [])

    events_text = "\n".join(
        f"  - {e['description']} (weight={e['weight']}, critical={e.get('is_critical', False)})"
        for e in events
    )
    coverage_text = "\n".join(f"  - {c}" for c in coverage)

    return [
        {"role": "system", "content": SYSTEM_VERSION_AWARE},
        {"role": "user", "content": (
            f"Write Manim CE code with the following STRICT CONSTRAINTS:\n\n"
            f"PROBLEM:\n{prompt}\n\n"
            f"CRITICAL VISUAL EVENTS (all must appear):\n{events_text}\n\n"
            f"COVERAGE REQUIREMENTS (labels/annotations):\n{coverage_text}\n\n"
            f"TIMING CONSTRAINTS:\n"
            f"  - Events must appear in the order listed above\n"
            f"  - Critical events MUST be present (non-negotiable)\n"
            f"  - Use self.play(anim1, anim2) for synchronized animations\n"
            f"  - Include self.wait() between major sections\n\n"
            f"TECHNICAL CONSTRAINTS:\n"
            f"  - Use `from manim import *`\n"
            f"  - Single Scene class only\n"
            f"  - No deprecated API (no ShowCreation, no CONFIG dict, no GraphScene)\n"
            f"  - Use Create() not ShowCreation(), Tex() not OldTex()\n\n"
            f"Output ONLY the Python code."
        )},
    ]


# ---------------------------------------------------------------------------
# 5. Version-conflict-aware
# ---------------------------------------------------------------------------

def _version_aware(problem: dict) -> list[dict[str, str]]:
    prompt = problem["full_prompt"]
    vcn = problem.get("version_conflict_notes", {})
    incompatibilities = vcn.get("known_incompatibilities", [])

    conflicts_text = "\n".join(f"  - {c}" for c in incompatibilities[:10])

    return [
        {"role": "system", "content": SYSTEM_VERSION_AWARE},
        {"role": "user", "content": (
            f"Write Manim CE code for the following problem.\n\n"
            f"PROBLEM:\n{prompt}\n\n"
            f"⚠️  VERSION TRAPS — This problem's original code used ManimGL. "
            f"The following GL constructs MUST NOT appear in your code:\n"
            f"{conflicts_text}\n\n"
            f"Use ONLY Manim CE compatible constructs. "
            f"Use `from manim import *`. Output ONLY the Python code."
        )},
    ]


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def get_strategy_names() -> list[str]:
    """Return list of available strategy names."""
    return ["zero_shot", "few_shot", "cot", "constraint", "version_aware"]
