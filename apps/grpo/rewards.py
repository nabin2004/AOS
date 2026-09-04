"""ManiBench reward functions for GRPO training.

Maps ManiBench metrics to scalar rewards:
  - executability (50%): syntax + Scene class; optional manim render
  - alignment (25%): blended lexical presence + live OpenCLIP frame similarity (when rendered)
  - vcer (15%): ManimGL / deprecated API penalty
  - coverage (10%): pedagogical term density
  - length penalty: subtracted from combined score
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import DEFAULT_LENGTH_PENALTY_COEF
from manibench import get_alignment_events, get_coverage_terms, get_vcer_patterns

# Try importing live OpenCLIP reward module from grpo_dataset
GRPO_ROOT = Path(__file__).resolve().parents[1]
GRPO_DATASET_ROOT = GRPO_ROOT / "grpo_dataset"
if str(GRPO_DATASET_ROOT) not in sys.path:
    sys.path.insert(0, str(GRPO_DATASET_ROOT))

try:
    from reward_model.clip_reward import compute_video_clip_reward
except Exception:
    compute_video_clip_reward = None

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
                if isinstance(base, ast.Name) and base.id in ("Scene", "VoiceoverScene", "ThreeDScene", "MovingCameraScene"):
                    return True
                if isinstance(base, ast.Attribute) and base.attr in ("Scene", "VoiceoverScene", "ThreeDScene", "MovingCameraScene"):
                    return True
    return False


def _heuristic_exec_score(code: str) -> float:
    source = _extract_python(code)
    
    score = 0.0
    # Baseline formatting rewards so truncated candidates don't flatline to 0.0
    if "```python" in code.lower() or "```" in code:
        score += 0.10
    if "class " in code and "Scene" in code:
        score += 0.10
        
    if _syntax_ok(source):
        score += 0.05
        if _has_manim_scene(source):
            score = max(score, HEURISTIC_EXEC_PARTIAL)
            
    return score


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


def _find_visual_events_path(problem_id: str) -> Optional[Path]:
    """Locate visual_events.json file for problem_id."""
    if not problem_id:
        return None
    data_root = os.environ.get("MANIBENCH_DATA_ROOT")
    if data_root:
        candidate = Path(data_root) / "problems" / problem_id / "visual_events.json"
        if candidate.is_file():
            return candidate
    candidate = GRPO_DATASET_ROOT / "data" / "problems" / problem_id / "visual_events.json"
    if candidate.is_file():
        return candidate
    return None


def executability_reward(completions: list[object], **kwargs) -> list[float]:
    texts = _normalize_completions(completions)
    run_render = os.environ.get("MANIBENCH_GRPO_RENDER", "0") == "1"
    rewards = []
    rendered_videos = []
    
    for code in texts:
        if not run_render:
            rewards.append(_heuristic_exec_score(code))
            rendered_videos.append(None)
            continue
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                script = Path(tmpdir) / "scene.py"
                script.write_text(_extract_python(code), encoding="utf-8")
                result = subprocess.run(
                    ["manim", "-pql", "--media_dir", str(tmpdir), str(script)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=tmpdir,
                )
                if result.returncode == 0:
                    rewards.append(1.0)
                    mp4s = list(Path(tmpdir).rglob("*.mp4"))
                    rendered_videos.append(str(mp4s[0]) if mp4s else None)
                else:
                    rewards.append(0.0)
                    rendered_videos.append(None)
        except Exception:
            rewards.append(0.0)
            rendered_videos.append(None)
            
    # Stash rendered videos in kwargs for visual reward if passed as dict
    if "rendered_videos" in kwargs and isinstance(kwargs["rendered_videos"], list):
        kwargs["rendered_videos"].clear()
        kwargs["rendered_videos"].extend(rendered_videos)
        
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


def lexical_alignment_reward(completions: list[object], **kwargs) -> list[float]:
    """First-stage fast lexical presence check for ManiBench required_visual_events."""
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


def clip_visual_reward(
    completions: list[object],
    rendered_videos: Optional[list[Optional[str]]] = None,
    **kwargs,
) -> list[float]:
    """Second-stage live OpenCLIP visual reward on rendered video frames."""
    texts = _normalize_completions(completions)
    problem_ids = kwargs.get("problem_id", [""] * len(texts))
    rewards = []
    
    if compute_video_clip_reward is None:
        return [0.0] * len(texts)

    for idx, (code, pid) in enumerate(zip(texts, problem_ids)):
        video_path = rendered_videos[idx] if rendered_videos and idx < len(rendered_videos) else None
        ve_path = _find_visual_events_path(pid)

        if not video_path or not Path(video_path).is_file() or not ve_path:
            rewards.append(0.0)
            continue

        try:
            res = compute_video_clip_reward(video_path, ve_path, fps=2.0)
            rewards.append(float(res.score))
        except Exception:
            rewards.append(0.0)

    return rewards


def alignment_reward(completions: list[object], **kwargs) -> list[float]:
    """Composite alignment combining fast lexical filter and live OpenCLIP visual reward."""
    lexical_r = lexical_alignment_reward(completions, **kwargs)
    use_clip = os.environ.get("MANIBENCH_GRPO_CLIP_REWARD", "0") == "1"
    
    if not use_clip:
        return lexical_r
        
    rendered_videos = kwargs.get("rendered_videos")
    clip_r = clip_visual_reward(completions, rendered_videos=rendered_videos, **kwargs)
    
    # Blend: 50% lexical presence + 50% semantic OpenCLIP temporal alignment
    blended = [0.50 * lex + 0.50 * vis for lex, vis in zip(lexical_r, clip_r)]
    return blended


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
    rendered_videos: list[Optional[str]] = []
    exec_r = executability_reward(completions, rendered_videos=rendered_videos, **kwargs)
    vcer_r = vcer_reward(completions, **kwargs)
    align_r = alignment_reward(completions, rendered_videos=rendered_videos, **kwargs)
    cover_r = coverage_reward(completions, **kwargs)
    
    w = REWARD_WEIGHTS
    n = len(completions)
    penalties = _length_penalty(kwargs.get("completion_ids"), n)
    combined = []
    for e, v, a, c, pen in zip(exec_r, vcer_r, align_r, cover_r, penalties):
        # Hard executability gate: if code lacks basic format, reward is 0.0
        if e < 0.15:
            combined.append(0.0)
            continue
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
