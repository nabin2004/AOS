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
import shutil
import subprocess
import sys
import tempfile
import uuid
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
    from reward_model.clip_reward import (
        compute_prompt_image_clip_reward,
        compute_video_clip_reward,
    )
except Exception:
    compute_video_clip_reward = None
    compute_prompt_image_clip_reward = None

try:
    from vlm_judge import (
        DEFAULT_VLM_MODEL,
        DEFAULT_VLM_THRESHOLD,
        evaluate_cascading_ensemble,
        get_gemma_judge,
    )
except Exception:
    get_gemma_judge = None
    evaluate_cascading_ensemble = None

_RENDER_BASE_DIR = Path(tempfile.gettempdir()) / "aos_grpo_renders"


def _ensure_render_dir() -> Path:
    _RENDER_BASE_DIR.mkdir(parents=True, exist_ok=True)
    return _RENDER_BASE_DIR

_CODE_FENCE = re.compile(r"```(?:python)?\s*([\s\S]*?)```", re.IGNORECASE)

HEURISTIC_EXEC_PARTIAL = 0.3
REWARD_WEIGHTS = {
    "exec": 0.45,
    "narration": 0.15,
    "align": 0.20,
    "vcer": 0.10,
    "cover": 0.10,
}
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
    # Strip thinking tags if present
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()

    # 1. Closed code fence (standard ```python ... ```)
    m = _CODE_FENCE.search(text)
    if m:
        return m.group(1).strip()

    # 2. Truncated code fence where closing ``` was never emitted
    lowered = text.lower()
    if "```python" in lowered:
        idx = lowered.find("```python")
        extracted = text[idx + len("```python"):].strip()
        if "```" in extracted:
            extracted = extracted[:extracted.find("```")].strip()
        return extracted
    elif "```" in text:
        idx = text.find("```")
        extracted = text[idx + 3:].strip()
        lines = extracted.splitlines()
        if lines and lines[0].strip().isalpha():
            lines = lines[1:]
        extracted = "\n".join(lines).strip()
        if "```" in extracted:
            extracted = extracted[:extracted.find("```")].strip()
        return extracted

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
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id in ("Scene", "VoiceoverScene", "ThreeDScene", "MovingCameraScene"):
                        return True
                    if isinstance(base, ast.Attribute) and base.attr in ("Scene", "VoiceoverScene", "ThreeDScene", "MovingCameraScene"):
                        return True
    except SyntaxError:
        pass

    # Fallback regex check: allows detecting Scene classes even if the file was truncated at the end
    scene_pattern = re.compile(
        r"class\s+\w+\s*\(\s*(?:[\w\.]*\.)?(?:Scene|VoiceoverScene|ThreeDScene|MovingCameraScene)\s*\)",
        re.IGNORECASE,
    )
    return bool(scene_pattern.search(source))


def _heuristic_exec_score(code: str) -> float:
    source = _extract_python(code)

    score = 0.0
    # Baseline formatting rewards so truncated candidates don't flatline to 0.0
    if "```python" in code.lower() or "```" in code:
        score += 0.10
    if "class " in code and any(s in code for s in ("Scene", "VoiceoverScene", "ThreeDScene", "MovingCameraScene")):
        score += 0.10
    if "def construct" in code:
        score += 0.10
    if "self.play(" in code or "self.add(" in code:
        score += 0.10

    has_scene = _has_manim_scene(source)
    if _syntax_ok(source):
        score += 0.10
        if has_scene:
            score = max(score, HEURISTIC_EXEC_PARTIAL + 0.10)
    else:
        if has_scene:
            score = max(score, HEURISTIC_EXEC_PARTIAL)

    return min(1.0, score)


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

    batch_dir = kwargs.get("batch_dir")
    if batch_dir is None:
        batch_token = kwargs.get("batch_id") or uuid.uuid4().hex[:8]
        batch_dir = _ensure_render_dir() / f"batch_{batch_token}"
        batch_dir.mkdir(parents=True, exist_ok=True)
    
    for idx, code in enumerate(texts):
        if not run_render:
            rewards.append(_heuristic_exec_score(code))
            rendered_videos.append(None)
            continue
        try:
            comp_dir = batch_dir / f"comp_{idx}"
            comp_dir.mkdir(parents=True, exist_ok=True)
            script = comp_dir / "scene.py"
            script.write_text(_extract_python(code), encoding="utf-8")
            result = subprocess.run(
                ["manim", "-pql", "--media_dir", str(comp_dir), str(script)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(comp_dir),
            )
            if result.returncode == 0:
                rewards.append(1.0)
                mp4s = list(comp_dir.rglob("*.mp4"))
                rendered_videos.append(str(mp4s[0]) if mp4s else None)
            else:
                # Non-rendering code receives partial heuristic score so reward doesn't collapse to 0.0
                rewards.append(0.5 * _heuristic_exec_score(code))
                rendered_videos.append(None)
        except Exception:
            rewards.append(0.5 * _heuristic_exec_score(code))
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


def narration_reward(completions: list[object], **kwargs) -> list[float]:
    """Rewards VoiceoverScene inheritance, speech service initialization, and synchronized voiceover context blocks."""
    texts = _normalize_completions(completions)
    rewards = []
    for code in texts:
        score = 0.0
        # 1. VoiceoverScene inheritance
        if re.search(r"class\s+\w+\s*\(\s*(?:[\w\.]*\.)?VoiceoverScene\s*\)", code):
            score += 0.35
        elif "VoiceoverScene" in code:
            score += 0.20

        # 2. Speech service setup (AOSSpeechService / GTTSService / RecorderService)
        if any(term in code for term in ("set_speech_service", "AOSSpeechService", "GTTSService", "RecorderService")):
            score += 0.25

        # 3. Synchronized voiceover context block: with self.voiceover(...)
        if re.search(r"with\s+self\.voiceover\s*\(", code):
            score += 0.40
        elif "voiceover(" in code:
            score += 0.20

        rewards.append(min(1.0, score))
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


def visual_alignment_reward(
    completions: list[object],
    rendered_videos: Optional[list[Optional[str]]] = None,
    **kwargs,
) -> list[float]:
    """Live visual alignment reward strictly evaluated on GPU 1 (cuda:1).

    Supports:
    - mode="ensemble" (default): Cascading Reward Filter (OpenCLIP fast filter + Gemma 4/PaliGemma expert grader)
    - mode="gemma": Pure Gemma/PaliGemma VLM layout and correctness judge
    - mode="clip": Pure OpenCLIP semantic frame similarity
    """
    texts = _normalize_completions(completions)
    problem_ids = kwargs.get("problem_id", [""] * len(texts))
    prompts = kwargs.get("prompts", kwargs.get("prompt", [""] * len(texts)))
    if isinstance(prompts, (str, dict)):
        prompts = [prompts] * len(texts)
    prompts_text = [_completion_text(p) for p in prompts]
    if len(prompts_text) < len(texts):
        prompts_text.extend([""] * (len(texts) - len(prompts_text)))

    reward_device = os.environ.get("AOS_REWARD_DEVICE")
    if not reward_device:
        import torch
        reward_device = "cuda:1" if torch.cuda.is_available() and torch.cuda.device_count() >= 2 else "cuda:0"

    judge_mode = os.environ.get("AOS_VLM_JUDGE", "ensemble").lower().strip()
    vlm_model = os.environ.get("AOS_VLM_MODEL")
    threshold = float(os.environ.get("AOS_VLM_THRESHOLD", "0.15"))

    rewards = []

    for idx, (code, pid, prompt_text) in enumerate(zip(texts, problem_ids, prompts_text)):
        video_path = rendered_videos[idx] if rendered_videos and idx < len(rendered_videos) else None

        if not video_path or not Path(video_path).is_file():
            rewards.append(0.0)
            continue

        ve_path = _find_visual_events_path(pid)

        try:
            # 1. Cascading Ensemble Mode (OpenCLIP fast filter -> Gemma VLM expert layout grader)
            if judge_mode == "ensemble" and evaluate_cascading_ensemble is not None:
                score, meta = evaluate_cascading_ensemble(
                    video_path=video_path,
                    prompt=prompt_text,
                    threshold=threshold,
                    device=reward_device,
                    model_id=vlm_model,
                )
                if _reward_debug_enabled():
                    print(f"  [vlm-ensemble] {meta}", file=sys.stderr, flush=True)
                rewards.append(float(score))

            # 2. Pure Gemma / PaliGemma VLM Judge Mode
            elif judge_mode == "gemma" and get_gemma_judge is not None:
                judge = get_gemma_judge(model_id=vlm_model, device=reward_device)
                score = judge.evaluate_video(video_path, prompt_text)
                rewards.append(float(score))

            # 3. Fast OpenCLIP Baseline Mode
            elif ve_path and compute_video_clip_reward is not None:
                res = compute_video_clip_reward(video_path, ve_path, fps=2.0, device=reward_device)
                rewards.append(float(res.score))
            elif compute_prompt_image_clip_reward is not None:
                score = compute_prompt_image_clip_reward(video_path, prompt_text, fps=2.0, device=reward_device)
                rewards.append(float(score))
            else:
                rewards.append(0.5)
        except Exception as e:
            if _reward_debug_enabled():
                print(f"  [visual-reward-error] {e}", file=sys.stderr, flush=True)
            rewards.append(0.0)

    return rewards


# Retain clip_visual_reward as backward-compatible alias
clip_visual_reward = visual_alignment_reward


def alignment_reward(completions: list[object], **kwargs) -> list[float]:
    """Composite alignment combining fast lexical filter and live VLM / OpenCLIP visual reward."""
    lexical_r = lexical_alignment_reward(completions, **kwargs)
    use_clip = os.environ.get("MANIBENCH_GRPO_CLIP_REWARD", "0") == "1"
    
    if not use_clip:
        return lexical_r
        
    rendered_videos = kwargs.get("rendered_videos")
    vis_r = visual_alignment_reward(completions, rendered_videos=rendered_videos, **kwargs)
    
    # Blend: 50% lexical presence + 50% visual alignment (evaluated strictly on cuda:1)
    blended = [0.50 * lex + 0.50 * vis for lex, vis in zip(lexical_r, vis_r)]
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
    batch_token = uuid.uuid4().hex[:8]
    batch_dir = _ensure_render_dir() / f"batch_{batch_token}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    rendered_videos: list[Optional[str]] = []

    try:
        kwargs["batch_dir"] = batch_dir
        kwargs["batch_id"] = batch_token

        exec_r = executability_reward(completions, rendered_videos=rendered_videos, **kwargs)
        narr_r = narration_reward(completions, **kwargs)
        vcer_r = vcer_reward(completions, **kwargs)
        align_r = alignment_reward(completions, rendered_videos=rendered_videos, **kwargs)
        cover_r = coverage_reward(completions, **kwargs)
        
        w = REWARD_WEIGHTS
        n = len(completions)
        penalties = _length_penalty(kwargs.get("completion_ids"), n)
        combined = []
        for e, nr, v, a, c, pen in zip(exec_r, narr_r, vcer_r, align_r, cover_r, penalties):
            score = w["exec"] * e + w["narration"] * nr + w["align"] * a + w["vcer"] * v + w["cover"] * c - pen
            # Soft penalty instead of hard collapse to 0.0:
            # If code completely lacks basic structure (e < 0.10), dampen score by 75%
            if e < 0.10:
                score *= 0.25
            combined.append(max(0.0, min(1.0, score)))

        if _reward_debug_enabled() and combined:
            print(
                f"[reward] min={min(combined):.3f} max={max(combined):.3f} "
                f"mean={sum(combined) / len(combined):.3f} "
                f"exec={sum(exec_r) / len(exec_r):.3f} "
                f"narr={sum(narr_r) / len(narr_r):.3f} "
                f"align={sum(align_r) / len(align_r):.3f} "
                f"vcer={sum(vcer_r) / len(vcer_r):.3f} "
                f"cover={sum(cover_r) / len(cover_r):.3f}",
                file=sys.stderr,
                flush=True,
            )
        return combined
    finally:
        if batch_dir.exists():
            shutil.rmtree(batch_dir, ignore_errors=True)
