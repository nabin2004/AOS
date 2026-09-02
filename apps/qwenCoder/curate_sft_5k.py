#!/usr/bin/env python3
"""Curate a 5,000-sample high-impact targeted ManimCE SFT dataset.

Targeted buckets:
1. API Grounding & Traceback Correction (1,000 samples)
2. Updaters, ValueTrackers & Dynamic Animations (1,500 samples)
3. Scientific Computing & Math Libraries (NumPy, SciPy, SymPy) (1,500 samples)
4. Multi-Step Pedagogical & LaTeX Scenes (1,000 samples)

Usage:
    uv run python curate_sft_5k.py
    uv run python curate_sft_5k.py --output-dir ./curated_sft_5k --push --repo-id nabin2004/manim-sft-5k-targeted
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from manim_api_lint import (
    assignment_names,
    extract_python,
    is_lint_clean,
    lint_assistant_text,
)

QWEN_ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = "nabin2004/manim-sft"
DEFAULT_OUTPUT_DIR = QWEN_ROOT / "curated_sft_5k"
DEFAULT_REPO = "nabin2004/manim-sft-5k-targeted"
SEED = 42

BUCKET_TARGETS = {
    "api_and_error_correction": 1_000,
    "updaters_and_dynamics": 1_500,
    "scientific_and_math_compute": 1_500,
    "pedagogical_latex_scenes": 1_000,
}

SYSTEM = (
    "You are an expert Manim Community Edition Python (v0.19+) code generator. "
    "Use only documented constructor keyword arguments (never element_color, max_value, max_magnitude, or size). "
    "Always format LaTeX math using standard raw strings (e.g. r'w_1'), never Unicode subscripts (e.g. ₁). "
    "Leverage ValueTracker, always_redraw, add_updater, numpy, scipy, and sympy for accurate mathematical simulations."
)

COLORS = ("BLUE", "RED", "GREEN", "YELLOW", "ORANGE", "TEAL", "GOLD", "PURPLE", "MAROON")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _chat(
    user: str,
    assistant: str,
    *,
    bucket: str,
    source: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = {"source": source, "bucket": bucket, "quality_tier": "targeted_5k"}
    if extra:
        meta.update(extra)
    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "metadata": meta,
    }


def _wrap_scene(body: str, class_name: str = "DemoScene", extra_imports: str = "") -> str:
    imports = "from manim import *\nimport numpy as np\n"
    if extra_imports:
        imports += extra_imports + "\n"
    return (
        f"{imports}\n"
        f"class {class_name}(Scene):\n"
        "    def construct(self):\n"
        + "\n".join(f"        {line}" if line else "        " for line in body.splitlines())
        + "\n"
    )


# ==============================================================================
# BUCKET 1: API Grounding & Error Correction (1,000 samples)
# ==============================================================================

API_TEMPLATES = [
    ("Matrix", "Matrix([[1, 2], [3, 4]], left_bracket='[', right_bracket=']')"),
    ("DecimalMatrix", "DecimalMatrix([[1.23, 4.56], [7.89, 0.12]], num_decimal_places=2)"),
    ("Axes", "Axes(x_range=[-3, 3, 1], y_range=[-2, 4, 1], x_length=6, y_length=4, tips=True)"),
    ("NumberPlane", "NumberPlane(x_range=[-4, 4, 1], y_range=[-3, 3, 1], background_line_style={'stroke_opacity': 0.4})"),
    ("ArrowVectorField", "ArrowVectorField(lambda p: np.array([-p[1], p[0], 0]), x_range=[-3, 3, 1], y_range=[-3, 3, 1])"),
    ("StreamLines", "StreamLines(lambda p: np.array([-p[1], p[0], 0]), x_range=[-3, 3, 1], y_range=[-3, 3, 1], stroke_width=2)"),
    ("BarChart", "BarChart(values=[2, 4, 3, 5], bar_names=['A', 'B', 'C', 'D'], y_range=[0, 6, 2], y_length=4, x_length=6)"),
    ("Table", "Table([['1', '2'], ['3', '4']], col_labels=[Text('X'), Text('Y')], row_labels=[Text('R1'), Text('R2')])"),
    ("DecimalNumber", "DecimalNumber(3.14159, num_decimal_places=3, include_sign=False)"),
    ("TangentLine", "TangentLine(Circle(radius=1.5), alpha=0.25, length=3, color=YELLOW)"),
    ("RightAngle", "RightAngle(Line(ORIGIN, RIGHT), Line(ORIGIN, UP), length=0.4, quadrant=(1, 1))"),
    ("Brace", "Brace(Line(LEFT * 2, RIGHT * 2), direction=DOWN)"),
]

def synthesize_api_grounding(n: int, rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    i = 0
    while len(rows) < n:
        i += 1
        name, tmpl = API_TEMPLATES[i % len(API_TEMPLATES)]
        color = COLORS[i % len(COLORS)]
        body = (
            f"obj = {tmpl}\n"
            f"obj.set_color({color})\n"
            f"self.play(Create(obj))\n"
            f"self.wait(1)"
        )
        code = _wrap_scene(body, class_name=f"ApiValid{name}{i}")
        if not is_lint_clean(code):
            continue
        h = _hash_text(code)
        if h in seen:
            continue
        seen.add(h)
        user = (
            f"Construct a clean Manim CE scene initializing {name} with verified keyword arguments. "
            f"Ensure no deprecated ManimGL arguments (like element_color, max_value, or max_magnitude) are used."
        )
        rows.append(_chat(user, f"```python\n{code}```", bucket="api_and_error_correction", source="synth-api"))
    return rows


def _mutate_error_sample(code: str, mode: int) -> tuple[str, str]:
    if mode == 0:
        broken = code.replace("def construct(self):", "def construct(self):\n        m = Matrix([[1, 2]], element_color=RED)", 1)
        tb = "TypeError: Mobject.__init__() got an unexpected keyword argument 'element_color'"
    elif mode == 1:
        broken = code.replace("def construct(self):", "def construct(self):\n        ax = NumberLine(max_value=10)", 1)
        tb = "TypeError: Mobject.__init__() got an unexpected keyword argument 'max_value'"
    elif mode == 2:
        broken = code.replace("def construct(self):", "def construct(self):\n        txt = Text('Test', size=24)", 1)
        tb = "TypeError: Text.__init__() got an unexpected keyword argument 'size'"
    elif mode == 3:
        broken = code.replace("def construct(self):", "def construct(self):\n        t = MathTex('w\u2081 + x\u00b2')", 1)
        tb = "ValueError: latex error converting to dvi. Unicode character ₁ (U+2081) not supported."
    else:
        broken = code.rstrip() + "\n        self.play(FadeOut(undefined_variable_target))\n"
        tb = "NameError: name 'undefined_variable_target' is not defined in construct()"
    return broken, tb


def synthesize_traceback_repairs(clean_codes: list[str], n: int, rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not clean_codes:
        clean_codes = [_wrap_scene("dot = Dot(color=BLUE)\nself.play(FadeIn(dot))")]
    i = 0
    while len(rows) < n:
        code = clean_codes[i % len(clean_codes)]
        mode = i % 5
        i += 1
        broken, tb = _mutate_error_sample(code, mode)
        user = (
            f"The following Manim CE script crashed with this traceback:\n\n"
            f"```text\n{tb}\n```\n\n"
            f"Fix the bug and provide the corrected, fully compilable Manim CE code:\n\n"
            f"```python\n{broken}\n```"
        )
        rows.append(_chat(user, f"```python\n{code}```", bucket="api_and_error_correction", source="synth-error-repair"))
    return rows


# ==============================================================================
# BUCKET 2: Updaters, ValueTrackers & Dynamic Animations (1,500 samples)
# ==============================================================================

UPDATER_PATTERNS = [
    (
        "Tangent line dynamically tracking curve f(x) = x^2",
        """ax = Axes(x_range=[-3, 3, 1], y_range=[0, 9, 3], x_length=6, y_length=4)
curve = ax.plot(lambda x: x**2, color=BLUE)
t = ValueTracker(1.0)
dot = always_redraw(lambda: Dot(ax.c2p(t.get_value(), t.get_value()**2), color=RED))
tangent = always_redraw(lambda: ax.get_secant_slope_group(
    t.get_value(), curve, dx=0.01, dx_line_color=YELLOW, secant_line_length=3, secant_line_color=YELLOW
))
num = DecimalNumber(0, num_decimal_places=2, color=YELLOW).to_corner(UR)
num.add_updater(lambda m: m.set_value(t.get_value()))

self.add(ax, curve, dot, tangent, num)
self.play(t.animate.set_value(2.5), run_time=3)
self.play(t.animate.set_value(-2.0), run_time=3)""",
    ),
    (
        "Riemann Rectangles adapting dynamically with ValueTracker",
        """ax = Axes(x_range=[0, 4, 1], y_range=[0, 5, 1], x_length=6, y_length=4)
curve = ax.plot(lambda x: 0.5 * x**2, color=BLUE)
k = ValueTracker(4)
rects = always_redraw(lambda: ax.get_riemann_rectangles(
    curve, x_range=[0, 3], dx=3.0 / max(int(k.get_value()), 1), stroke_color=WHITE, fill_opacity=0.6
))
count_text = Integer(4).to_corner(UL)
count_text.add_updater(lambda m: m.set_value(int(k.get_value())))

self.add(ax, curve, rects, count_text)
self.play(k.animate.set_value(30), run_time=4, rate_func=linear)
self.wait(1)""",
    ),
    (
        "Orbital mechanics simulation using add_updater with dt",
        """sun = Dot(ORIGIN, radius=0.25, color=GOLD)
planet = Dot(RIGHT * 2.5, radius=0.12, color=BLUE)
trail = TracedPath(planet.get_center, stroke_color=BLUE_A, stroke_width=2, stroke_opacity=0.8)

angle = [0.0]
omega = 1.5  # rad/s

def update_planet(mob, dt):
    angle[0] += omega * dt
    mob.move_to(np.array([2.5 * np.cos(angle[0]), 1.8 * np.sin(angle[0]), 0]))

planet.add_updater(update_planet)
self.add(sun, trail, planet)
self.wait(4)
planet.clear_updaters()""",
    ),
    (
        "Dynamic vector between moving points with put_start_and_end_on",
        """dot1 = Dot(LEFT * 2 + DOWN, color=RED)
dot2 = Dot(RIGHT * 2 + UP, color=GREEN)
vec = Arrow(ORIGIN, RIGHT, color=YELLOW, buff=0)
vec.add_updater(lambda v: v.put_start_and_end_on(dot1.get_center(), dot2.get_center()))
label = always_redraw(lambda: DecimalNumber(
    np.linalg.norm(dot2.get_center() - dot1.get_center()), num_decimal_places=2
).next_to(vec, UP))

self.add(dot1, dot2, vec, label)
self.play(dot1.animate.shift(UP * 2), dot2.animate.shift(LEFT * 1.5), run_time=3)
self.play(dot1.animate.shift(RIGHT * 3), dot2.animate.shift(DOWN * 2), run_time=3)""",
    ),
    (
        "Cycloid Generation with TracedPath and rolling circle",
        """ground = Line(LEFT * 4 + DOWN * 1.5, RIGHT * 4 + DOWN * 1.5, color=GREY)
r = 0.8
theta = ValueTracker(0.0)

wheel = always_redraw(lambda: Circle(radius=r, color=WHITE).move_to(
    LEFT * 3 + RIGHT * (r * theta.get_value()) + DOWN * (1.5 - r)
))
dot = always_redraw(lambda: Dot(
    wheel.get_center() + np.array([-r * np.sin(theta.get_value()), -r * np.cos(theta.get_value()), 0]),
    color=RED, radius=0.08
))
trail = TracedPath(dot.get_center, stroke_color=YELLOW, stroke_width=3)

self.add(ground, trail, wheel, dot)
self.play(theta.animate.set_value(2 * PI * 1.2), run_time=4, rate_func=linear)
self.wait(1)""",
    ),
]


def synthesize_updaters(n: int, rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    i = 0
    while len(rows) < n:
        desc, body = UPDATER_PATTERNS[i % len(UPDATER_PATTERNS)]
        i += 1
        code = _wrap_scene(body, class_name=f"DynamicScene{i}")
        user = f"Create an interactive Manim CE animation demonstrating: {desc}. Use updaters and ValueTracker."
        rows.append(_chat(user, f"```python\n{code}```", bucket="updaters_and_dynamics", source="synth-updaters"))
    return rows


# ==============================================================================
# BUCKET 3: Scientific & Mathematical Computing (1,500 samples)
# ==============================================================================

SCIENTIFIC_PATTERNS = [
    (
        "Fourier Series Square Wave Approximation with NumPy",
        """ax = Axes(x_range=[-PI, PI, PI/2], y_range=[-1.5, 1.5, 0.5], x_length=7, y_length=4)
self.add(ax)

def fourier_square(x, n_terms):
    y = np.zeros_like(x)
    for k in range(1, n_terms + 1):
        n = 2 * k - 1
        y += (4.0 / (np.pi * n)) * np.sin(n * x)
    return y

for n in [1, 3, 7, 15]:
    curve = ax.plot(lambda x: fourier_square(np.array([x]), n)[0], color=interpolate_color(BLUE, YELLOW, n/15))
    label = MathTex(f"N = {n}").to_corner(UR)
    self.play(Create(curve), Write(label), run_time=1.5)
    self.wait(0.5)
    if n != 15:
        self.play(FadeOut(curve), FadeOut(label), run_time=0.5)""",
        "",
    ),
    (
        "Lorenz Attractor Differential Equation with SciPy solve_ivp",
        """from scipy.integrate import solve_ivp

def lorenz(t, state, sigma=10.0, rho=28.0, beta=8.0/3.0):
    x, y, z = state
    return [sigma * (y - x), x * (rho - z) - y, x * y - beta * z]

t_eval = np.linspace(0, 20, 2000)
sol = solve_ivp(lorenz, (0, 20), [1.0, 1.0, 1.0], t_eval=t_eval)

# Scale coordinates to fit Manim screen (2D projection x vs z)
points = [np.array([sol.y[0][i] * 0.15, (sol.y[2][i] - 25) * 0.12, 0]) for i in range(len(t_eval))]
path = VMobject(color=TEAL, stroke_width=2)
path.set_points_as_corners(points[:10])

dot = Dot(points[0], color=YELLOW, radius=0.08)
self.add(path, dot)

step = ValueTracker(10)
def update_path(mob):
    idx = int(step.get_value())
    mob.set_points_as_corners(points[:idx])

path.add_updater(update_path)
dot.add_updater(lambda d: d.move_to(points[min(int(step.get_value()), len(points)-1)]))

self.play(step.animate.set_value(len(points)-1), run_time=6, rate_func=linear)
self.wait(1)""",
        "from scipy.integrate import solve_ivp",
    ),
    (
        "SymPy Symbolic Derivative and animated derivation steps",
        r"""import sympy as sp

x = sp.Symbol('x')
f = sp.sin(x) * sp.exp(-x)
f_prime = sp.diff(f, x)

eq1 = MathTex(r"f(x) = " + sp.latex(f), color=BLUE).to_edge(UP)
eq2 = MathTex(r"f'(x) = \frac{d}{dx}\left(" + sp.latex(f) + r"\right)", color=YELLOW).next_to(eq1, DOWN, buff=0.6)
eq3 = MathTex(r"f'(x) = " + sp.latex(f_prime), color=GREEN).next_to(eq2, DOWN, buff=0.6)

self.play(Write(eq1))
self.wait(1)
self.play(Write(eq2))
self.wait(1)
self.play(TransformMatchingTex(eq2.copy(), eq3))
self.wait(2)""",
        "import sympy as sp",
    ),
    (
        "Linear Algebra 2D Matrix Eigenvector Transformation",
        r"""plane = NumberPlane(x_range=[-4, 4, 1], y_range=[-3, 3, 1])
A = np.array([[2.0, 1.0], [1.0, 2.0]])
eigenvalues, eigenvectors = np.linalg.eig(A)

v1 = eigenvectors[:, 0]
v2 = eigenvectors[:, 1]

vec1 = Arrow(ORIGIN, plane.c2p(v1[0], v1[1]), color=RED, buff=0)
vec2 = Arrow(ORIGIN, plane.c2p(v2[0], v2[1]), color=GREEN, buff=0)

label_v1 = MathTex(r"\mathbf{v}_1", color=RED).next_to(vec1.get_end(), UP)
label_v2 = MathTex(r"\mathbf{v}_2", color=GREEN).next_to(vec2.get_end(), RIGHT)

self.add(plane, vec1, vec2, label_v1, label_v2)
self.play(
    plane.animate.apply_matrix(A),
    vec1.animate.put_start_and_end_on(ORIGIN, plane.c2p(*(A @ v1))),
    vec2.animate.put_start_and_end_on(ORIGIN, plane.c2p(*(A @ v2))),
    run_time=3
)
self.wait(1)""",
        "",
    ),
]


def synthesize_scientific(n: int, rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    i = 0
    while len(rows) < n:
        desc, body, extra_imp = SCIENTIFIC_PATTERNS[i % len(SCIENTIFIC_PATTERNS)]
        i += 1
        code = _wrap_scene(body, class_name=f"SciComputeScene{i}", extra_imports=extra_imp)
        user = f"Write a Manim CE visualization using scientific Python libraries (numpy, scipy, sympy) for: {desc}."
        rows.append(_chat(user, f"```python\n{code}```", bucket="scientific_and_math_compute", source="synth-scientific"))
    return rows


# ==============================================================================
# BUCKET 4: Multi-Step Pedagogical & LaTeX Scenes (1,000 samples)
# ==============================================================================

PEDAGOGICAL_TEMPLATES = [
    (
        "Proof of Pythagorean Theorem via geometric rearrangement",
        r"""title = Title("Pythagorean Theorem: $a^2 + b^2 = c^2$")
formula = MathTex(r"a^2 + b^2 = c^2", color=YELLOW).next_to(title, DOWN, buff=0.5)
tri = Polygon(ORIGIN, RIGHT * 3, RIGHT * 3 + UP * 2, color=BLUE, fill_opacity=0.4)
brace_a = Brace(Line(ORIGIN, RIGHT * 3), direction=DOWN)
label_a = MathTex("a").next_to(brace_a, DOWN)
brace_b = Brace(Line(RIGHT * 3, RIGHT * 3 + UP * 2), direction=RIGHT)
label_b = MathTex("b").next_to(brace_b, RIGHT)
hyp = Line(ORIGIN, RIGHT * 3 + UP * 2, color=GOLD)
label_c = MathTex("c", color=GOLD).next_to(hyp.get_center(), UL)

self.play(Write(title))
self.play(Create(tri), FadeIn(brace_a, label_a), FadeIn(brace_b, label_b), Create(hyp), Write(label_c))
self.wait(1)
self.play(Write(formula))
self.wait(2)""",
    ),
    (
        "Taylor Series Expansion of exp(x)",
        r"""title = Title(r"Taylor Series of $f(x) = e^x$ around $x=0$")
ax = Axes(x_range=[-3, 3, 1], y_range=[-1, 8, 2], x_length=6, y_length=4)
exp_curve = ax.plot(lambda x: np.exp(x), color=WHITE)
exp_label = MathTex(r"e^x").next_to(ax.c2p(2, np.exp(2)), RIGHT)

t1 = ax.plot(lambda x: 1 + x, color=BLUE)
t2 = ax.plot(lambda x: 1 + x + 0.5 * x**2, color=GREEN)
t3 = ax.plot(lambda x: 1 + x + 0.5 * x**2 + (1/6) * x**3, color=YELLOW)

self.play(Write(title), Create(ax), Create(exp_curve), Write(exp_label))
self.play(Create(t1), run_time=1.5)
self.wait(0.5)
self.play(Transform(t1, t2), run_time=1.5)
self.wait(0.5)
self.play(Transform(t1, t3), run_time=1.5)
self.wait(2)""",
    ),
    (
        "Gradient Descent Optimization on 2D Quadratic Function",
        r"""title = Title(r"Gradient Descent: $x_{k+1} = x_k - \gamma \nabla f(x_k)$")
ax = Axes(x_range=[-3, 3, 1], y_range=[0, 9, 3], x_length=6, y_length=4)
parabola = ax.plot(lambda x: x**2, color=BLUE)

gamma = 0.4
x_val = 2.5
dot = Dot(ax.c2p(x_val, x_val**2), color=RED)

self.play(Write(title), Create(ax), Create(parabola), FadeIn(dot))
for step in range(5):
    grad = 2 * x_val
    next_x = x_val - gamma * grad
    arrow = Arrow(ax.c2p(x_val, x_val**2), ax.c2p(next_x, next_x**2), color=YELLOW, buff=0)
    self.play(GrowArrow(arrow), dot.animate.move_to(ax.c2p(next_x, next_x**2)), run_time=0.8)
    self.remove(arrow)
    x_val = next_x
self.wait(1)""",
    ),
]


def synthesize_pedagogical(n: int, rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    i = 0
    while len(rows) < n:
        desc, body = PEDAGOGICAL_TEMPLATES[i % len(PEDAGOGICAL_TEMPLATES)]
        i += 1
        code = _wrap_scene(body, class_name=f"PedagogicalScene{i}")
        user = f"Create a step-by-step educational Manim CE lecture scene explaining: {desc}."
        rows.append(_chat(user, f"```python\n{code}```", bucket="pedagogical_latex_scenes", source="synth-pedagogical"))
    return rows


# ==============================================================================
# MAIN CURATION & ASSEMBLY PIPELINE
# ==============================================================================

def curate_5k_dataset(output_dir: Path, push_to_hub: bool = False, repo_id: str | None = None) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "train.jsonl"

    print("=================================================================")
    print("🚀 Starting 5,000-Sample Targeted Manim SFT Dataset Curation")
    print(f"   Output destination: {out_file}")
    print("=================================================================")

    # Bucket 1: API Grounding (500) + Error Correction (500) = 1,000
    print("\n[1/4] Generating API Grounding & Error Correction (1,000 rows)...")
    api_rows = synthesize_api_grounding(500, rng)
    clean_codes = [extract_python(r["messages"][-1]["content"]) for r in api_rows]
    error_rows = synthesize_traceback_repairs(clean_codes, 500, rng)
    bucket1 = api_rows + error_rows
    print(f"      ✔ Bucket 1 generated: {len(bucket1)} samples")

    # Bucket 2: Updaters & Dynamics = 1,500
    print("\n[2/4] Generating Updaters & Dynamic Animations (1,500 rows)...")
    bucket2 = synthesize_updaters(1_500, rng)
    print(f"      ✔ Bucket 2 generated: {len(bucket2)} samples")

    # Bucket 3: Scientific Computing & Math Libraries = 1,500
    print("\n[3/4] Generating Scientific & Math Compute (1,500 rows)...")
    bucket3 = synthesize_scientific(1_500, rng)
    print(f"      ✔ Bucket 3 generated: {len(bucket3)} samples")

    # Bucket 4: Multi-Step Pedagogical & LaTeX Scenes = 1,000
    print("\n[4/4] Generating Pedagogical & LaTeX Scenes (1,000 rows)...")
    bucket4 = synthesize_pedagogical(1_000, rng)
    print(f"      ✔ Bucket 4 generated: {len(bucket4)} samples")

    # Combine and shuffle
    all_rows = bucket1 + bucket2 + bucket3 + bucket4
    rng.shuffle(all_rows)

    print(f"\nWriting {len(all_rows)} curated examples to {out_file}...")
    with out_file.open("w", encoding="utf-8") as f:
        for row in all_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"✔ Successfully saved {len(all_rows)} samples to {out_file}")

    if push_to_hub and repo_id:
        try:
            from datasets import load_dataset
            from huggingface_hub import HfApi
            print(f"Pushing dataset to Hugging Face Hub ({repo_id})...")
            ds = load_dataset("json", data_files=str(out_file))
            ds.push_to_hub(repo_id, private=False)
            print("✔ Dataset successfully pushed to Hugging Face Hub!")
        except Exception as exc:
            print(f"WARNING: Could not push to Hugging Face Hub: {exc}", file=sys.stderr)

    return all_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Curate a 5k targeted ManimCE SFT dataset")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--push", action="store_true", help="Push to Hugging Face Hub")
    parser.add_argument("--repo-id", default=DEFAULT_REPO, help="HF repo ID")
    args = parser.parse_args()

    curate_5k_dataset(args.output_dir, push_to_hub=args.push, repo_id=args.repo_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
