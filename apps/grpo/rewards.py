"""ManiBench reward functions for GRPO training.

Maps ManiBench metrics to scalar rewards:
  - executability (50%): syntax + Scene class; optional manim render
  - alignment (25%): required_visual_events pattern presence
  - vcer (15%): ManimGL / deprecated API penalty
  - coverage (10%): pedagogical term density
  - length penalty: subtracted from combined score
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from config import DEFAULT_LENGTH_PENALTY_COEF
from manibench import get_alignment_events, get_coverage_terms, get_vcer_patterns

_CODE_FENCE = re.compile(r"```(?:python)?\s*([\s\S]*?)```", re.IGNORECASE)

HEURISTIC_EXEC_PARTIAL = 0.3
REWARD_WEIGHTS = {"exec": 0.50, "align": 0.25, "vcer": 0.15, "cover": 0.10}
DEFAULT_COVERAGE_DIVISOR = 20.0


def _completion_text(completion: object) -> str:
    if isinstance(completion, list) and completion:
        first = completion[0]
        return first.get("content", "") if isinstance(first, dict) else str(first)
    if isinstance(completion, str):
        return completion
    return str(completion)


def _normalize_completions(completions: list[object]) -> list[str]:
    return [_completion_text(c) for c in completions]


def _extract_python(text: str) -> str:
    m = _CODE_FENCE.search(text)
    if m:
        return m.group(1).strip()
    return text.strip()


def _syntax_ok(source: str) -> bool:
    try:
        ast.parse(source)
    except SyntaxError:
        return False
    return True


def _has_manim_scene(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "Scene":
                    return True
                if isinstance(base, ast.Attribute) and base.attr == "Scene":
                    return True
    return False


def _heuristic_exec_score(code: str) -> float:
    source = _extract_python(code)
    if not _syntax_ok(source) or not _has_manim_scene(source):
        return 0.0
    return HEURISTIC_EXEC_PARTIAL


def _coverage_divisor() -> float:
    raw = os.environ.get("MANIBENCH_COVERAGE_DIVISOR", "")
    if raw:
        return float(raw)
    return DEFAULT_COVERAGE_DIVISOR


def _length_penalty_coef() -> float:
    raw = os.environ.get("MANIBENCH_LENGTH_PENALTY_COEF", "")
    if raw:
        return float(raw)
    return DEFAULT_LENGTH_PENALTY_COEF


def _max_completion_length() -> int:
    raw = os.environ.get("MANIBENCH_MAX_COMPLETION_LENGTH", "")
    if raw:
        return int(raw)
    return 512


def _length_penalty(
    completion_ids: list[list[int]] | None,
    n: int,
) -> list[float]:
    if not completion_ids:
        return [0.0] * n
    coef = _length_penalty_coef()
    max_len = max(_max_completion_length(), 1)
    penalties = []
    for ids in completion_ids:
        if ids is None:
            penalties.append(0.0)
        else:
            penalties.append(coef * (len(ids) / max_len))
    if len(penalties) < n:
        penalties.extend([0.0] * (n - len(penalties)))
    return penalties[:n]


def _reward_debug_enabled() -> bool:
    return os.environ.get("MANIBENCH_GRPO_REWARD_DEBUG", "0") == "1"


def executability_reward(completions: list[object], **kwargs) -> list[float]:
    texts = _normalize_completions(completions)
    run_render = os.environ.get("MANIBENCH_GRPO_RENDER", "0") == "1"
    rewards = []
    for code in texts:
        if not run_render:
            rewards.append(_heuristic_exec_score(code))
            continue
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                script = Path(tmpdir) / "scene.py"
                script.write_text(_extract_python(code), encoding="utf-8")
                result = subprocess.run(
                    ["manim", "-pql", str(script)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=tmpdir,
                )
                rewards.append(1.0 if result.returncode == 0 else 0.0)
        except Exception:
            rewards.append(0.0)
    return rewards


def vcer_reward(completions: list[object], **kwargs) -> list[float]:
    """Penalises ManimGL-specific patterns that break in Manim CE."""
    texts = _normalize_completions(completions)
    problem_ids = kwargs.get("problem_id", [""] * len(texts))
    rewards = []
    for code, pid in zip(texts, problem_ids):
        patterns = get_vcer_patterns(pid)
        conflicts = sum(1 for p in patterns if re.search(p, code, re.IGNORECASE))
        rewards.append(max(0.0, 1.0 - conflicts / len(patterns)))
    return rewards


def alignment_reward(completions: list[object], **kwargs) -> list[float]:
    """
    Weighted presence check for ManiBench required_visual_events.
    Score = Σ(weight_i × present_i) / Σ(weight_i)
    Events without detectable patterns receive 0.0 (no partial credit).
    """
    texts = _normalize_completions(completions)
    problem_ids = kwargs.get("problem_id", [""] * len(texts))
    rewards = []
    for code, pid in zip(texts, problem_ids):
        events = get_alignment_events(pid)
        if not events:
            rewards.append(1.0)
            continue
        total_w = sum(w for w, _ in events)
        score = 0.0
        for weight, patterns in events:
            if not patterns:
                continue
            if any(re.search(p, code) for p in patterns):
                score += weight
        rewards.append(score / total_w)
    return rewards


_FALLBACK_PATTERNS = {
    "math": [r"Tex\(", r"MathTex\(", r"\\[a-zA-Z]+", r"\blabel\b"],
    "visual": [r"set_color\(", r"set_fill\(", r"Arrow\(", r"Dot\(", r"Rectangle\("],
    "numeric": [
        r"DecimalNumber\(",
        r"Integer\(",
        r"ValueTracker\(",
        r"Axes\(",
        r"NumberLine\(",
    ],
    "structural": [
        r"VGroup\(",
        r"Group\(",
        r"arrange\(",
        r"wait\(",
        r"LaggedStart\(",
        r"Succession\(",
    ],
}
_FALLBACK_WEIGHTS = {"math": 0.35, "visual": 0.30, "numeric": 0.20, "structural": 0.15}


def coverage_reward(completions: list[object], **kwargs) -> list[float]:
    """Fraction of per-problem coverage terms found; falls back to category weights."""
    texts = _normalize_completions(completions)
    problem_ids = kwargs.get("problem_id", [""] * len(texts))
    divisor = _coverage_divisor()
    rewards = []
    for code, pid in zip(texts, problem_ids):
        terms = get_coverage_terms(pid)
        if terms:
            found = sum(1 for t in terms if re.search(rf"\b{re.escape(t)}\b", code))
            rewards.append(found / len(terms))
        else:
            cat_scores = {
                cat: min(
                    sum(len(re.findall(p, code, re.IGNORECASE)) for p in pats)
                    / divisor,
                    1.0,
                )
                for cat, pats in _FALLBACK_PATTERNS.items()
            }
            rewards.append(
                sum(_FALLBACK_WEIGHTS[c] * cat_scores[c] for c in _FALLBACK_WEIGHTS)
            )
    return rewards


def combined_reward(completions: list[object], **kwargs) -> list[float]:
    exec_r = executability_reward(completions, **kwargs)
    vcer_r = vcer_reward(completions, **kwargs)
    align_r = alignment_reward(completions, **kwargs)
    cover_r = coverage_reward(completions, **kwargs)
    w = REWARD_WEIGHTS
    n = len(completions)
    penalties = _length_penalty(kwargs.get("completion_ids"), n)
    combined = []
    for e, v, a, c, pen in zip(exec_r, vcer_r, align_r, cover_r, penalties):
        score = w["exec"] * e + w["align"] * a + w["vcer"] * v + w["cover"] * c - pen
        combined.append(max(0.0, min(1.0, score)))

    if _reward_debug_enabled() and combined:
        print(
            f"[reward] min={min(combined):.3f} max={max(combined):.3f} "
            f"mean={sum(combined) / len(combined):.3f} "
            f"exec={sum(exec_r) / len(exec_r):.3f} "
            f"align={sum(align_r) / len(align_r):.3f} "
            f"vcer={sum(vcer_r) / len(vcer_r):.3f} "
            f"cover={sum(cover_r) / len(cover_r):.3f}",
            file=sys.stderr,
            flush=True,
        )
    return combined
