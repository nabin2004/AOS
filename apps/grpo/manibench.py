"""ManiBench pilot dataset loader and reward metadata for GRPO training."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from datasets import Dataset
from huggingface_hub import hf_hub_download

from config import TrainingConfig, hub_token

REPO_ID = "nabin2004/ManiBench"
PILOT_FILE = "ManiBench_Pilot_Dataset.json"

_PROMPT_PREFIX = (
    "Write valid Manim Community Edition (CE) Python code.\n"
    "Use `from manim import *`. Output a complete Scene class in a ```python fence.\n\n"
)

_STOP_WORDS = {
    "the",
    "and",
    "for",
    "that",
    "this",
    "with",
    "from",
    "are",
    "was",
    "were",
    "been",
    "have",
    "has",
    "will",
    "would",
    "could",
    "should",
    "each",
    "then",
    "than",
    "when",
    "where",
    "which",
    "while",
    "what",
    "about",
    "after",
    "before",
    "between",
    "both",
    "during",
    "either",
    "every",
    "more",
    "most",
    "much",
    "many",
    "only",
    "other",
    "some",
    "such",
    "also",
    "just",
    "like",
    "must",
    "present",
    "used",
    "using",
    "correctly",
    "properly",
    "shown",
    "show",
    "display",
    "visible",
}

_MANIM_KEYWORDS = [
    "Create",
    "Write",
    "Transform",
    "FadeIn",
    "FadeOut",
    "Arrow",
    "Dot",
    "Axes",
    "NumberPlane",
    "MathTex",
    "Tex",
    "Text",
    "DecimalNumber",
    "ValueTracker",
    "VGroup",
    "AnimationGroup",
    "Succession",
    "LaggedStart",
    "TracedPath",
    "Indicate",
    "Circle",
    "Rectangle",
    "Line",
    "Vector",
    "ThreeDScene",
    "Surface",
    "add_updater",
    "always_redraw",
    "wait",
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


_PROBLEM_INDEX: dict[str, ProblemMeta] = {}


def format_user_prompt(full_prompt: str) -> list[dict[str, str]]:
    return [{"role": "user", "content": _PROMPT_PREFIX + full_prompt}]


def load_pilot_problems(config: TrainingConfig) -> list[dict[str, Any]]:
    if config.dataset_path is not None:
        payload = json.loads(config.dataset_path.read_text(encoding="utf-8"))
    else:
        path = hf_hub_download(
            config.dataset_repo,
            PILOT_FILE,
            repo_type="dataset",
            token=hub_token(),
        )
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload["problems"]


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
    event_id = event.get("id", "")
    combined = f"{event_id} {description}"
    patterns: list[str] = []

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


def _build_problem_index(problems: list[dict[str, Any]]) -> dict[str, ProblemMeta]:
    index: dict[str, ProblemMeta] = {}
    for problem in problems:
        pid = problem["id"]
        events = [
            (float(ev.get("weight", 1.0)), _patterns_for_event(ev))
            for ev in problem.get("required_visual_events") or []
        ]
        coverage_terms: list[str] = []
        for req in problem.get("coverage_requirements") or []:
            coverage_terms.extend(_extract_keywords(str(req)))

        vcer_patterns = list(GL_ONLY_PATTERNS)
        notes = problem.get("version_conflict_notes") or {}
        for incompat in notes.get("known_incompatibilities") or []:
            vcer_patterns.extend(_patterns_for_incompat(str(incompat)))

        index[pid] = ProblemMeta(
            alignment_events=events,
            coverage_terms=sorted(set(coverage_terms)),
            vcer_patterns=vcer_patterns,
        )
    return index


def ensure_index(config: TrainingConfig) -> None:
    global _PROBLEM_INDEX
    if _PROBLEM_INDEX:
        return
    _PROBLEM_INDEX = _build_problem_index(load_pilot_problems(config))


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
    if config.prompts_path is not None:
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
                row = {
                    "prompt": format_user_prompt(text),
                    "problem_id": obj.get("id") or f"traj_{i}",
                    "full_prompt": text,
                }
                for _ in range(max(1, config.repeat_factor)):
                    rows.append(dict(row))
        if not rows:
            raise ValueError(f"No prompts loaded from {config.prompts_path}")
        return Dataset.from_list(rows)

    ensure_index(config)
    problems = load_pilot_problems(config)
    rows = []

    for problem in problems:
        row = {
            "prompt": format_user_prompt(problem["full_prompt"]),
            "problem_id": problem["id"],
            "full_prompt": problem["full_prompt"],
        }
        for _ in range(config.repeat_factor):
            rows.append(dict(row))

    return Dataset.from_list(rows)
