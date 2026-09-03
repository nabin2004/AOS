"""ManiBench & Manim-grpo-dataset-200 dataset loader and reward metadata for GRPO training."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from datasets import Dataset
from huggingface_hub import hf_hub_download

from config import TrainingConfig, hub_token

DEFAULT_GRPO_DATASET_REPO = "nabin2004/Manim-grpo-dataset-200"
PILOT_REPO = "nabin2004/ManiBench"
PILOT_FILE = "ManiBench_Pilot_Dataset.json"

_PROMPT_PREFIX = (
    "Write valid Manim Community Edition (CE) Python code.\n"
    "Use `from manim import *`. Output a complete Scene class in a ```python fence.\n\n"
)

_STOP_WORDS = {
    "the", "and", "for", "that", "this", "with", "from", "are", "was", "were", "been",
    "have", "has", "will", "would", "could", "should", "each", "then", "than", "when",
    "where", "which", "while", "what", "about", "after", "before", "between", "both",
    "during", "either", "every", "more", "most", "much", "many", "only", "other", "some",
    "such", "also", "just", "like", "must", "present", "used", "using", "correctly",
    "properly", "shown", "show", "display", "visible",
}

_MANIM_KEYWORDS = [
    "Create", "Write", "Transform", "FadeIn", "FadeOut", "Arrow", "Dot", "Axes",
    "NumberPlane", "MathTex", "Tex", "Text", "DecimalNumber", "ValueTracker",
    "VGroup", "AnimationGroup", "Succession", "LaggedStart", "TracedPath",
    "Indicate", "Circle", "Rectangle", "Line", "Vector", "ThreeDScene",
    "Surface", "add_updater", "always_redraw", "wait", "voiceover", "VoiceoverScene",
]

GL_ONLY_PATTERNS: list[str] = [
    r"from\s+manim_imports_ext",
    r"from\s+manimlib",
    r"from\s+manim_gl",
    r"import\s+manim_imports_ext",
    r"class\s+\w+\s*\(\s*GraphScene\s*\)",
    r"class\s+\w+\s*\(\s*InteractiveScene\s*\)",
    r"ShowCreation\s*\(",
    r"FadeInFrom\s*\(",
    r"PiCreature\s*\(",
    r"GlowDot\s*\(",
    r"\.embed\s*\(",
    r"force_skipping\s*\(",
    r"self\.frame\.",
    r"OldTex\s*\(",
    r"TexMobject\s*\(",
    r"TextMobject\s*\(",
    r"fix_in_frame\s*\(",
    r"set_shading\s*\(",
]


@dataclass
class ProblemMeta:
    alignment_events: list[tuple[float, list[str]]] = field(default_factory=list)
    coverage_terms: list[str] = field(default_factory=list)
    vcer_patterns: list[str] = field(default_factory=list)
    clip_events: list[dict[str, Any]] = field(default_factory=list)


_PROBLEM_INDEX: dict[str, ProblemMeta] = {}


def format_user_prompt(full_prompt: str) -> list[dict[str, str]]:
    return [{"role": "user", "content": _PROMPT_PREFIX + full_prompt}]


def _extract_keywords(text: str, *, min_len: int = 4) -> list[str]:
    words = re.findall(r"[A-Za-z_]\w+", text)
    seen: set[str] = set()
    out: list[str] = []
    for word in words:
        key = word.lower()
        if len(word) < min_len or key in _STOP_WORDS or key in seen:
            continue
        seen.add(key)
        out.append(word)
    return out


def _patterns_for_event(event: dict[str, Any]) -> list[str]:
    description = event.get("description", "")
    event_id = event.get("event_id") or event.get("id", "")
    keyword_bank = event.get("keyword_bank", [])
    
    patterns: list[str] = []
    if keyword_bank:
        for kw in keyword_bank:
            if kw.endswith("("):
                patterns.append(re.escape(kw[:-1]) + r"\s*\(")
            else:
                patterns.append(rf"\b{re.escape(kw)}\b")

    combined = f"{event_id} {description}"
    for word in _extract_keywords(combined):
        patterns.append(rf"\b{re.escape(word)}\b")

    for kw in _MANIM_KEYWORDS:
        if kw.lower() in combined.lower():
            patterns.append(re.escape(kw) + r"\s*\(")

    for obj in re.findall(r"[A-Z][a-zA-Z]+", description):
        if len(obj) >= 4:
            patterns.append(re.escape(obj) + r"\s*\(")

    return (
        patterns or [re.escape(description[:32])]
        if description
        else [r"self\.play\s*\("]
    )


def _patterns_for_incompat(incompat: str) -> list[str]:
    before = incompat.split("→")[0].strip()
    keywords = re.findall(r"\w+", before)
    patterns: list[str] = []
    for kw in keywords:
        if len(kw) >= 4:
            patterns.append(re.escape(kw))
    return patterns


def _resolve_problem_dir(problem_id: str, config: TrainingConfig) -> Optional[Path]:
    """Locate problem directory locally or download from HF."""
    # 1. Check local grpo_dataset/data/problems/
    local_candidates = [
        Path(__file__).resolve().parents[1] / "grpo_dataset" / "data" / "problems" / problem_id,
        Path(__file__).resolve().parents[2] / "apps" / "grpo_dataset" / "data" / "problems" / problem_id,
    ]
    if config.dataset_path:
        local_candidates.insert(0, Path(config.dataset_path).parent / "problems" / problem_id)

    for cand in local_candidates:
        if cand.is_dir():
            return cand

    return None


def _load_problem_meta(problem_id: str, config: TrainingConfig) -> ProblemMeta:
    """Load metadata for a single problem from local bundle or HF cache."""
    pdir = _resolve_problem_dir(problem_id, config)
    events: list[tuple[float, list[str]]] = []
    coverage_terms: list[str] = []
    vcer_patterns = list(GL_ONLY_PATTERNS)
    clip_events: list[dict[str, Any]] = []

    if pdir and pdir.is_dir():
        # 1. Load visual_events.json
        ve_path = pdir / "visual_events.json"
        if ve_path.is_file():
            try:
                ve_data = json.loads(ve_path.read_text(encoding="utf-8"))
                for ev in ve_data.get("events", []):
                    w = float(ev.get("weight", 1.0))
                    events.append((w, _patterns_for_event(ev)))
                    clip_events.append(ev)
            except Exception:
                pass

        # 2. Load coverage.json
        cov_path = pdir / "coverage.json"
        if cov_path.is_file():
            try:
                cov_data = json.loads(cov_path.read_text(encoding="utf-8"))
                reqs = cov_data.get("requirements", {})
                for cat, val in reqs.items():
                    if isinstance(val, dict):
                        expected = val.get("expected", [])
                        for exp in expected:
                            coverage_terms.extend(_extract_keywords(str(exp)))
                    elif isinstance(val, list):
                        for exp in val:
                            coverage_terms.extend(_extract_keywords(str(exp)))
            except Exception:
                pass

        # 3. Load version_notes.json
        vn_path = pdir / "version_notes.json"
        if vn_path.is_file():
            try:
                vn_data = json.loads(vn_path.read_text(encoding="utf-8"))
                for conf in vn_data.get("conflicts", []):
                    gl = conf.get("gl_construct")
                    if gl:
                        vcer_patterns.append(re.escape(gl))
            except Exception:
                pass

    return ProblemMeta(
        alignment_events=events,
        coverage_terms=sorted(set(coverage_terms)),
        vcer_patterns=vcer_patterns,
        clip_events=clip_events,
    )


def load_dataset_split(config: TrainingConfig, split_name: str = "train") -> list[dict[str, Any]]:
    """Loads dataset rows from local or Hugging Face Hub (200-problem bundle format)."""
    global _PROBLEM_INDEX

    # Check for custom prompt override
    if config.prompts_path is not None and config.prompts_path.is_file():
        rows: list[dict[str, Any]] = []
        with config.prompts_path.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                text = (
                    obj.get("prompt")
                    or obj.get("user_prompt")
                    or obj.get("full_prompt")
                    or ""
                ).strip()
                if not text:
                    continue
                pid = obj.get("id") or f"traj_{i}"
                rows.append({"id": pid, "prompt": text, "full_prompt": text})
        return rows

    # Check local grpo_dataset split file
    local_split_candidates = [
        Path(__file__).resolve().parents[1] / "grpo_dataset" / "data" / "splits" / f"{split_name}.jsonl",
        Path(__file__).resolve().parents[2] / "apps" / "grpo_dataset" / "data" / "splits" / f"{split_name}.jsonl",
    ]
    if config.dataset_path:
        local_split_candidates.insert(0, Path(config.dataset_path))

    split_file_path = None
    for cand in local_split_candidates:
        if cand.is_file() and cand.stat().st_size > 0:
            split_file_path = cand
            break

    # If not local, download from HF Hub
    if split_file_path is None:
        repo_id = config.dataset_repo or DEFAULT_GRPO_DATASET_REPO
        try:
            downloaded = hf_hub_download(
                repo_id=repo_id,
                filename=f"data/splits/{split_name}.jsonl",
                repo_type="dataset",
                token=hub_token(),
            )
            split_file_path = Path(downloaded)
        except Exception:
            # Fallback to legacy pilot dataset
            try:
                downloaded = hf_hub_download(
                    repo_id=PILOT_REPO,
                    filename=PILOT_FILE,
                    repo_type="dataset",
                    token=hub_token(),
                )
                payload = json.loads(Path(downloaded).read_text(encoding="utf-8"))
                return payload.get("problems", [])
            except Exception as e:
                raise FileNotFoundError(f"Failed to load dataset from local or HF: {e}")

    rows: list[dict[str, Any]] = []
    with open(split_file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            pid = item.get("id")
            prompt = item.get("prompt") or item.get("full_prompt") or ""
            
            # Index problem meta
            if pid and pid not in _PROBLEM_INDEX:
                _PROBLEM_INDEX[pid] = _load_problem_meta(pid, config)

            rows.append({
                "id": pid,
                "prompt": prompt,
                "full_prompt": prompt,
                "problem_path": item.get("problem_path", ""),
            })

    return rows


def ensure_index(config: TrainingConfig) -> None:
    global _PROBLEM_INDEX
    if _PROBLEM_INDEX:
        return
    _ = load_dataset_split(config, "train")


def get_alignment_events(problem_id: str) -> list[tuple[float, list[str]]]:
    meta = _PROBLEM_INDEX.get(problem_id)
    return meta.alignment_events if meta else []


def get_coverage_terms(problem_id: str) -> list[str]:
    meta = _PROBLEM_INDEX.get(problem_id)
    return meta.coverage_terms if meta else []


def get_vcer_patterns(problem_id: str) -> list[str]:
    meta = _PROBLEM_INDEX.get(problem_id)
    return meta.vcer_patterns if meta else list(GL_ONLY_PATTERNS)


def build_dataset(config: TrainingConfig) -> Dataset:
    ensure_index(config)
    problems = load_dataset_split(config, "train")
    
    rows = []
    for problem in problems:
        row = {
            "prompt": format_user_prompt(problem["full_prompt"]),
            "problem_id": problem["id"],
            "full_prompt": problem["full_prompt"],
        }
        for _ in range(max(1, config.repeat_factor)):
            rows.append(dict(row))

    if not rows:
        raise ValueError("No problem rows loaded for GRPO dataset.")
    return Dataset.from_list(rows)
