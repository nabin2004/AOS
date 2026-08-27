#!/usr/bin/env python3
"""Curate a 10k high-impact Manim CE SFT mix from nabin2004/manim-sft.

Static lint only (no render). Synthesizes API-grounding, error-correction, and
LaTeX rows targeting ManiBench MB-002/004/006/008/011 failure modes.

Usage (from apps/qwenCoder):

    uv run python curate_sft_10k.py
    uv run python curate_sft_10k.py --push --repo-id nabin2004/manim-sft-10k
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

from manim_api_lint import (
    assignment_names,
    coverage_flags,
    extract_python,
    is_coverage_rich,
    is_lint_clean,
    lint_assistant_text,
)

QWEN_ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = "nabin2004/manim-sft"
DEFAULT_REPO = "nabin2004/manim-sft-10k"
DEFAULT_TOTAL = 10_000
SEED = 42

BUCKET_TARGETS = {
    "api_grounding": 800,
    "error_correction": 1_500,
    "latex": 700,
    "long_scene": 2_000,
    "coverage_rich": 2_500,
    "stratified_rest": 2_500,
}

SYSTEM = (
    "You write Manim Community Edition Python (v0.19+). Use only documented "
    "constructor keyword arguments (never element_color, max_value, or "
    "max_magnitude). Map spoken math to LaTeX like w_1, never Unicode "
    "subscripts. Keep names in scope across the full construct() method. "
    "Prefer LaggedStart, Transform, and layered FadeIn/FadeOut over a single "
    "sparse animation when the prompt asks for a full scene."
)

COLORS = ("BLUE", "RED", "GREEN", "YELLOW", "ORANGE", "TEAL", "GOLD", "PURPLE")

API_CTORS: tuple[tuple[str, str], ...] = (
    ("Circle", "Circle(radius=1.0, color={color})"),
    ("Dot", "Dot(ORIGIN, color={color})"),
    ("Square", "Square(side_length=1.5, color={color})"),
    ("Rectangle", "Rectangle(width=2, height=1, color={color})"),
    ("Line", "Line(LEFT, RIGHT, color={color})"),
    ("DashedLine", "DashedLine(LEFT, RIGHT, color={color})"),
    ("Arrow", "Arrow(LEFT, RIGHT, color={color}, buff=0.1)"),
    ("Vector", "Vector(RIGHT, color={color})"),
    ("Polygon", "Polygon(LEFT, UP, RIGHT, color={color})"),
    ("RegularPolygon", "RegularPolygon(n=6, color={color})"),
    ("Triangle", "Triangle(color={color})"),
    ("Star", "Star(n=5, color={color})"),
    ("Arc", "Arc(radius=1, start_angle=0, angle=PI, color={color})"),
    ("Ellipse", "Ellipse(width=2, height=1, color={color})"),
    ("Annulus", "Annulus(inner_radius=0.5, outer_radius=1, color={color})"),
    ("Text", 'Text("Manim CE", color={color})'),
    ("MathTex", 'MathTex(r"x^2 + y^2 = r^2", color={color})'),
    ("Tex", r'Tex(r"Hello", color={color})'),
    ("Title", 'Title("Eigenvectors")'),
    ("NumberLine", "NumberLine(x_range=[-3, 3, 1], color={color})"),
    ("Axes", "Axes(x_range=[-2, 2, 1], y_range=[-2, 2, 1], tips=False)"),
    ("NumberPlane", "NumberPlane(x_range=[-3, 3, 1], y_range=[-2, 2, 1])"),
    ("ThreeDAxes", "ThreeDAxes(x_range=[-2, 2, 1], y_range=[-2, 2, 1], z_range=[-2, 2, 1])"),
    ("Matrix", "Matrix([[1, 0], [0, 1]], left_bracket='[', right_bracket=']')"),
    ("DecimalMatrix", "DecimalMatrix([[1.5, 0], [0, 2.5]])"),
    ("IntegerMatrix", "IntegerMatrix([[1, 2], [3, 4]])"),
    ("VGroup", "VGroup(Dot(LEFT), Dot(RIGHT)).set_color({color})"),
    ("Brace", "Brace(Line(LEFT, RIGHT), direction=DOWN)"),
    ("SurroundingRectangle", "SurroundingRectangle(Text('box'), color={color})"),
    ("DecimalNumber", "DecimalNumber(3.14, num_decimal_places=2, color={color})"),
    ("Integer", "Integer(7, color={color})"),
    ("BarChart", "BarChart(values=[1, 3, 2], bar_names=['a', 'b', 'c'])"),
    ("Angle", "Angle(Line(ORIGIN, RIGHT), Line(ORIGIN, UP), radius=0.4)"),
    ("RightAngle", "RightAngle(Line(ORIGIN, RIGHT), Line(ORIGIN, UP), length=0.3)"),
    ("TangentLine", "TangentLine(Circle(), alpha=0.2, length=2)"),
    ("FunctionGraph", "FunctionGraph(lambda t: t**2, x_range=[-1, 1], color={color})"),
    ("ParametricFunction", "ParametricFunction(lambda t: np.array([np.cos(t), np.sin(t), 0]), t_range=[0, TAU])"),
    ("Sphere", "Sphere(radius=1, color={color})"),
    ("Cube", "Cube(side_length=1, fill_opacity=0.5, color={color})"),
    ("Code", 'Code(code_string="x = 1", language="python")'),
    ("Table", "Table([['1', '2'], ['3', '4']])"),
    ("IntegerTable", "IntegerTable([[1, 2], [3, 4]])"),
    ("NumberLine", "NumberLine(x_range=[-3, 3, 1], color={color})"),
    ("StreamLines", "StreamLines(lambda p: np.array([-p[1], p[0], 0]), max_anchors_per_line=5)"),
    ("ArrowVectorField", "ArrowVectorField(lambda p: np.array([-p[1], p[0], 0]))"),
    ("PolarPlane", "PolarPlane()"),
    ("ComplexPlane", "ComplexPlane()"),
    ("MobjectTable", "MobjectTable([[Integer(1), Integer(2)]])"),
    ("DecimalTable", "DecimalTable([[1.1, 2.2], [3.3, 4.4]])"),
    ("Group", "Group(Dot(), Text('g'))"),
    ("VMobject", "VMobject().set_points_as_corners([LEFT, UP, RIGHT]).set_color({color})"),
    ("FadeIn", "Circle(color={color})"),
    ("LaggedStart", "VGroup(Dot(LEFT, color={color}), Dot(RIGHT, color={color}))"),
)

LATEX_PAIRS: tuple[tuple[str, str], ...] = (
    ("w subscript 1", r"w_1"),
    ("w subscript 2", r"w_2"),
    ("x subscript i", r"x_i"),
    ("x subscript n", r"x_n"),
    ("a subscript 0", r"a_0"),
    ("lambda subscript 1", r"\lambda_1"),
    ("lambda subscript 2", r"\lambda_2"),
    ("theta subscript k", r"\theta_k"),
    ("partial f over partial x", r"\frac{\partial f}{\partial x}"),
    ("one half m v squared", r"\frac{1}{2} m v^2"),
    ("e to the i pi", r"e^{i\pi}"),
    ("sum from i equals 1 to n", r"\sum_{i=1}^{n}"),
    ("integral from 0 to x", r"\int_0^x"),
    ("integral of f prime of t dt", r"\int_0^x f'(t)\,dt"),
    ("f of x minus f of 0", r"f(x) - f(0)"),
    ("nabla dot F", r"\nabla \cdot F"),
    ("bold e subscript 1", r"\mathbf{e}_1"),
    ("bold e subscript 2", r"\mathbf{e}_2"),
    ("matrix 1 0 0 1", r"\begin{bmatrix} 1 & 0 \\ 0 & 1 \end{bmatrix}"),
    ("P of A given B", r"P(A \mid B)"),
    ("Bayes theorem", r"P(A \mid B) = \frac{P(B \mid A) P(A)}{P(B)}"),
    ("Taylor remainder", r"R_n(x)"),
    ("sin theta", r"\sin \theta"),
    ("cos 2 theta", r"\cos 2\theta"),
    ("sqrt of 2", r"\sqrt{2}"),
    ("infinity", r"\infty"),
    ("alpha plus beta", r"\alpha + \beta"),
    ("mu subscript 0", r"\mu_0"),
    ("sigma squared", r"\sigma^2"),
    ("hat y", r"\hat{y}"),
    ("bar x", r"\bar{x}"),
    ("norm of v", r"\|v\|"),
    ("inner product u v", r"\langle u, v \rangle"),
    ("set of real numbers", r"\mathbb{R}"),
    ("set of integers", r"\mathbb{Z}"),
    ("n choose k", r"\binom{n}{k}"),
    ("limit as n to infinity", r"\lim_{n \to \infty}"),
    ("d y d x", r"\frac{dy}{dx}"),
    ("second derivative of f", r"f''(x)"),
    ("log of x", r"\log x"),
    ("ln of x plus 1", r"\ln(x+1)"),
    ("e to the minus x squared", r"e^{-x^2}"),
    ("fraction 1 over 2 pi", r"\frac{1}{2\pi}"),
    ("omega subscript n", r"\omega_n"),
    ("phi subscript 0", r"\phi_0"),
    ("psi subscript n", r"\psi_n"),
    ("delta x", r"\Delta x"),
    ("partial squared T over partial x squared", r"\frac{\partial^2 T}{\partial x^2}"),
    ("gradient of f", r"\nabla f"),
    ("curl of F", r"\nabla \times F"),
    ("determinant of A", r"\det A"),
    ("trace of A", r"\mathrm{tr}(A)"),
    ("identity matrix I", r"I"),
    ("eigenvalue lambda", r"\lambda"),
    ("eigenvector v", r"\mathbf{v}"),
    ("dot product a b", r"\mathbf{a} \cdot \mathbf{b}"),
    ("cross product a b", r"\mathbf{a} \times \mathbf{b}"),
    ("unit vector i hat", r"\hat{\imath}"),
    ("probability of X", r"P(X)"),
    ("expected value of X", r"\mathbb{E}[X]"),
    ("variance of X", r"\mathrm{Var}(X)"),
    ("chi squared", r"\chi^2"),
    ("degrees of freedom nu", r"\nu"),
    ("Fourier transform", r"\hat{f}(\xi)"),
    ("wave function psi of x", r"\psi(x)"),
    ("energy E subscript n", r"E_n"),
    ("Planck h bar", r"\hbar"),
    ("speed of light c", r"c"),
    ("mass m subscript 0", r"m_0"),
    ("force F equals m a", r"F = ma"),
)


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
    meta = {"source": source, "bucket": bucket, "quality_tier": "high"}
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


def _wrap_scene(body: str, class_name: str = "Demo") -> str:
    return (
        "from manim import *\n"
        "import numpy as np\n\n"
        f"class {class_name}(Scene):\n"
        "    def construct(self):\n"
        + "\n".join(f"        {line}" if line else "        " for line in body.splitlines())
        + "\n"
    )


def assistant_code(row: dict[str, Any]) -> str:
    messages = row.get("messages") or []
    for msg in reversed(messages):
        if msg.get("role") == "assistant" and msg.get("content"):
            return extract_python(str(msg["content"]))
    return extract_python(str(row.get("final_code") or ""))


def user_prompt(row: dict[str, Any]) -> str:
    messages = row.get("messages") or []
    for msg in messages:
        if msg.get("role") == "user" and msg.get("content"):
            return str(msg["content"]).strip()
    return str(row.get("user_prompt") or row.get("prompt") or "").strip()


def corpus_row(row: dict[str, Any], bucket: str, source: str) -> dict[str, Any]:
    code = assistant_code(row)
    user = user_prompt(row) or "Write a Manim Community Edition scene for this topic."
    assistant = code if code.startswith("from manim") else f"```python\n{code}\n```"
    if not assistant.startswith("```") and "from manim" in assistant:
        assistant = f"```python\n{assistant}\n```"
    return _chat(user, assistant, bucket=bucket, source=source)


def synthesize_api(n: int, rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    ctors = list(API_CTORS)
    i = 0
    while len(rows) < n and i < n * 8:
        i += 1
        name, tmpl = ctors[i % len(ctors)]
        color = COLORS[i % len(COLORS)]
        expr = tmpl.format(color=color)
        if name == "LaggedStart":
            body = (
                f"mobs = {expr}\n"
                "self.play(LaggedStart(*[FadeIn(m) for m in mobs]))"
            )
        else:
            body = f"mob = {expr}\nself.play(FadeIn(mob))"
        code = _wrap_scene(body, class_name=f"Api{name}{i}")
        if not is_lint_clean(code):
            continue
        key = _hash_text(code)
        if key in seen:
            continue
        seen.add(key)
        user = (
            f"Show a minimal Manim CE example that constructs {name} with valid "
            f"keyword arguments only. Do not invent kwargs such as element_color, "
            f"max_value, or max_magnitude."
        )
        rows.append(
            _chat(
                user,
                f"```python\n{code}```",
                bucket="api_grounding",
                source="synthetic-api",
                extra={"class_name": name},
            )
        )
    return rows


def synthesize_latex(n: int, rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pairs = list(LATEX_PAIRS)
    i = 0
    while len(rows) < n:
        spoken, latex = pairs[i % len(pairs)]
        color = COLORS[i % len(COLORS)]
        i += 1
        code = _wrap_scene(
            f'label = MathTex(r"{latex}", color={color})\n'
            "self.play(Write(label))\n",
            class_name=f"Tex{i}",
        )
        if not is_lint_clean(code):
            continue
        user = (
            f'Create a Manim CE scene that typesets "{spoken}" with MathTex. '
            "Use LaTeX subscripts/superscripts (for example w_1), never Unicode "
            "characters such as ₁."
        )
        rows.append(
            _chat(
                user,
                f"```python\n{code}```",
                bucket="latex",
                source="synthetic-latex",
            )
        )
    return rows[:n]


def _mutate_element_color(code: str) -> tuple[str, str] | None:
    broken = code.replace(
        "def construct(self):",
        "def construct(self):\n        bad = Matrix([[1, 0], [0, 1]], element_color=RED)",
        1,
    )
    tb = (
        "TypeError: Mobject.__init__() got an unexpected keyword argument "
        "'element_color'"
    )
    return broken, tb


def _mutate_max_value(code: str) -> tuple[str, str] | None:
    broken = code.replace(
        "def construct(self):",
        "def construct(self):\n        bad = NumberLine(max_value=10)",
        1,
    )
    tb = "TypeError: Mobject.__init__() got an unexpected keyword argument 'max_value'"
    return broken, tb


def _mutate_max_magnitude(code: str) -> tuple[str, str] | None:
    broken = code.replace(
        "def construct(self):",
        "def construct(self):\n        bad = ArrowVectorField(lambda p: p, max_magnitude=2)",
        1,
    )
    tb = (
        "TypeError: Mobject.__init__() got an unexpected keyword argument "
        "'max_magnitude'"
    )
    return broken, tb


def _mutate_c2p(code: str) -> tuple[str, str] | None:
    broken = code.replace(
        "def construct(self):",
        "def construct(self):\n        axes_group = VGroup(NumberLine(), NumberLine())\n"
        "        p = axes_group.c2p(1, 0)",
        1,
    )
    tb = "AttributeError: VGroup object has no attribute 'c2p'"
    return broken, tb


def _mutate_unicode(code: str) -> tuple[str, str] | None:
    broken = code.replace(
        "def construct(self):",
        'def construct(self):\n        bad = MathTex("w\u2081")',
        1,
    )
    tb = "ValueError: latex error converting to dvi. Unicode character ₁ (U+2081)"
    return broken, tb


def _mutate_nameerror(code: str) -> tuple[str, str] | None:
    names = [n for n in assignment_names(code) if n not in {"self", "np"}]
    if len(names) < 2:
        return None
    victim = names[-1]
    # Reference an extra undefined name in a FadeOut
    broken = code.rstrip() + f"\n        self.play(FadeOut({victim}_missing))\n"
    tb = f"NameError: name '{victim}_missing' is not defined"
    return broken, tb


def _mutate_animation_non_mobject(code: str) -> tuple[str, str] | None:
    broken = code.replace(
        "def construct(self):",
        "def construct(self):\n        self.play(1.5)",
        1,
    )
    tb = "TypeError: Animation only works on Mobjects"
    return broken, tb


MUTATORS = (
    _mutate_element_color,
    _mutate_max_value,
    _mutate_max_magnitude,
    _mutate_c2p,
    _mutate_unicode,
    _mutate_nameerror,
    _mutate_animation_non_mobject,
)


def synthesize_errors(
    clean_codes: list[str], n: int, rng: random.Random
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not clean_codes:
        clean_codes = [
            _wrap_scene("circ = Circle(color=BLUE)\nself.play(Create(circ))")
        ]
    rng.shuffle(clean_codes)
    i = 0
    while len(rows) < n:
        code = clean_codes[i % len(clean_codes)]
        mut = MUTATORS[i % len(MUTATORS)]
        i += 1
        result = mut(code)
        if result is None:
            continue
        broken, tb = result
        user = (
            "The following Manim CE scene failed to compile. Truncated traceback:\n\n"
            f"{tb}\n\n"
            "Fix the code. Return a complete working scene. Do not keep the invalid "
            "constructor kwargs or Unicode subscripts.\n\n"
            f"```python\n{broken}\n```"
        )
        rows.append(
            _chat(
                user,
                f"```python\n{code}```",
                bucket="error_correction",
                source="synthetic-error",
                extra={"traceback": tb[:200]},
            )
        )
    return rows[:n]


def take_unique(
    candidates: list[dict[str, Any]],
    n: int,
    used: set[str],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in candidates:
        assistant = row["messages"][-1]["content"]
        key = _hash_text(assistant)
        if key in used:
            continue
        used.add(key)
        out.append(row)
        if len(out) >= n:
            break
    return out


def load_hub(repo: str, split: str = "train"):
    from datasets import load_dataset

    return load_dataset(repo, split=split)


def filter_corpus(ds, source: str) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for row in ds:
        code = assistant_code(row)
        if not code or len(code) < 40:
            continue
        if lint_assistant_text(code):
            continue
        flags = coverage_flags(code)
        kept.append(
            {
                "row": row,
                "code": code,
                "source": source,
                "flags": flags,
                "names": len(assignment_names(code)),
            }
        )
    return kept


def rank_long(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda it: (it["flags"]["play"], it["names"], it["flags"]["lines"]),
        reverse=True,
    )


def stratified(items: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
    if not items:
        return []
    items = list(items)
    items.sort(key=lambda it: it["flags"]["lines"])
    bins = 4
    size = max(len(items) // bins, 1)
    groups = [items[i : i + size] for i in range(0, len(items), size)]
    for g in groups:
        rng.shuffle(g)
    ordered: list[dict[str, Any]] = []
    remaining = True
    while remaining:
        remaining = False
        for g in groups:
            if g:
                ordered.append(g.pop())
                remaining = True
    return ordered


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _push(repo_id: str, train_path: Path, card_path: Path) -> None:
    from huggingface_hub import HfApi

    from hub_upload import require_token

    token = require_token()
    api = HfApi()
    api.create_repo(repo_id, repo_type="dataset", exist_ok=True, token=token)
    api.upload_file(
        path_or_fileobj=str(train_path),
        path_in_repo="data/train.jsonl",
        repo_id=repo_id,
        repo_type="dataset",
        token=token,
    )
    api.upload_file(
        path_or_fileobj=str(card_path),
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="dataset",
        token=token,
    )
    print(f"Pushed https://huggingface.co/datasets/{repo_id}")


def build_card(counts: dict[str, int]) -> str:
    lines = [
        "---",
        "license: apache-2.0",
        "task_categories:",
        "  - text-generation",
        "language:",
        "  - en",
        "tags:",
        "  - manim",
        "  - code-generation",
        "  - sft",
        "size_categories:",
        "  - 1K<n<10K",
        "---",
        "",
        "# manim-sft-10k",
        "",
        "Curated 10k Manim Community Edition chat SFT mix. Filtered from "
        "[`nabin2004/manim-sft`](https://huggingface.co/datasets/nabin2004/manim-sft) "
        "with a static API-signature linter (no full render pass), then mixed with "
        "synthetic API-grounding, error-correction, and LaTeX rows that target "
        "ManiBench failures (invalid kwargs, Unicode subscripts, NameError, sparse coverage).",
        "",
        "The original 38k corpus is unchanged.",
        "",
        "## Mix",
        "",
        "| Bucket | Rows |",
        "|--------|------|",
    ]
    for name, n in counts.items():
        lines.append(f"| `{name}` | {n} |")
    lines += [
        f"| **total** | **{sum(counts.values())}** |",
        "",
        "## Schema",
        "",
        "Chat `messages` (system / user / assistant) plus `metadata.bucket`.",
        "",
        "```python",
        "from datasets import load_dataset",
        f'ds = load_dataset("{DEFAULT_REPO}", split="train")',
        "```",
        "",
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--educlaw", default="", help="Optional extra Hub repo")
    parser.add_argument("--total", type=int, default=DEFAULT_TOTAL)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--out-dir", type=Path, default=QWEN_ROOT / "curated_sft_10k")
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--repo-id", default=DEFAULT_REPO)
    parser.add_argument("--limit-source", type=int, default=0, help="Debug: lint only N source rows")
    return parser.parse_args()


def scale_targets(total: int) -> dict[str, int]:
    base = sum(BUCKET_TARGETS.values())
    if total == base:
        return dict(BUCKET_TARGETS)
    scaled = {k: max(1, round(v * total / base)) for k, v in BUCKET_TARGETS.items()}
    drift = total - sum(scaled.values())
    scaled["stratified_rest"] = max(0, scaled["stratified_rest"] + drift)
    return scaled


def main() -> int:
    args = parse_args()
    rng = random.Random(args.seed)
    targets = scale_targets(args.total)
    used: set[str] = set()

    print(f"Loading {args.source}", flush=True)
    ds = load_hub(args.source)
    if args.limit_source:
        ds = ds.select(range(min(args.limit_source, len(ds))))
    print(f"Linting {len(ds)} rows", flush=True)
    pool = filter_corpus(ds, args.source)
    print(f"Lint-clean: {len(pool)}", flush=True)

    if args.educlaw:
        print(f"Loading extra {args.educlaw}", flush=True)
        extra = filter_corpus(load_hub(args.educlaw), args.educlaw)
        pool.extend(extra)
        print(f"Lint-clean with educlaw: {len(pool)}", flush=True)

    api_rows = synthesize_api(targets["api_grounding"], rng)
    latex_rows = synthesize_latex(targets["latex"], rng)
    error_rows = synthesize_errors([it["code"] for it in pool[:4000]], targets["error_correction"], rng)

    chosen: list[dict[str, Any]] = []
    chosen += take_unique(api_rows, targets["api_grounding"], used)
    chosen += take_unique(latex_rows, targets["latex"], used)
    chosen += take_unique(error_rows, targets["error_correction"], used)

    long_cands = [
        corpus_row(it["row"], "long_scene", it["source"])
        for it in rank_long(pool)
        if it["flags"]["play"] >= 3 or it["flags"]["lines"] >= 40
    ]
    chosen += take_unique(long_cands, targets["long_scene"], used)

    cov_cands = [
        corpus_row(it["row"], "coverage_rich", it["source"])
        for it in pool
        if is_coverage_rich(it["code"])
    ]
    rng.shuffle(cov_cands)
    chosen += take_unique(cov_cands, targets["coverage_rich"], used)

    rest_cands = [
        corpus_row(it["row"], "stratified_rest", it["source"])
        for it in stratified(pool, rng)
    ]
    chosen += take_unique(rest_cands, targets["stratified_rest"], used)

    if len(chosen) < args.total:
        filler = take_unique(rest_cands + long_cands + cov_cands, args.total - len(chosen), used)
        for row in filler:
            row["metadata"]["bucket"] = "stratified_rest"
        chosen += filler

    if len(chosen) > args.total:
        chosen = chosen[: args.total]

    rng.shuffle(chosen)
    counts: dict[str, int] = {}
    for row in chosen:
        bucket = str(row["metadata"]["bucket"])
        counts[bucket] = counts.get(bucket, 0) + 1

    out_dir: Path = args.out_dir
    train_path = out_dir / "data" / "train.jsonl"
    card_path = out_dir / "README.md"
    _write_jsonl(train_path, chosen)
    card_path.write_text(build_card(counts), encoding="utf-8")
    print(f"Wrote {len(chosen)} rows -> {train_path}")
    print("buckets:", counts)

    if args.push:
        _push(args.repo_id, train_path, card_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
