"""Audit HITL prompt and skill-token usage against a 32k context window.

Run from ``apps/ui/aos/backend`` with:

    uv run python scripts/count_hitl_context.py --stage composer --text "Fourier Transform"

This is a preflight estimate. Provider-reported ``input_tokens`` from a real
run can differ because providers serialize tool schemas and messages slightly
differently, and some skill capabilities may be loaded on demand.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

CONTEXT_WINDOW = 32_000
DEFAULT_MODEL = "gpt-4o"


@dataclass(frozen=True)
class ContextPart:
    name: str
    text: str


def _load_tokenizer(model: str) -> Callable[[str], int]:
    try:
        import tiktoken
    except ImportError as exc:
        raise SystemExit(
            "tiktoken is required for exact estimates. Run `uv sync` in the "
            "backend directory, or install tiktoken in the backend environment."
        ) from exc

    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return lambda text: len(encoding.encode(text, disallowed_special=()))


def _skill_files(
    skill_names: tuple[str, ...],
    skills_dir: Path,
    *,
    include_all_files: bool,
) -> list[ContextPart]:
    parts: list[ContextPart] = []
    for skill_name in skill_names:
        skill_dir = skills_dir / skill_name
        if not skill_dir.is_dir():
            continue
        paths = sorted(skill_dir.rglob("*.md")) if include_all_files else [skill_dir / "SKILL.md"]
        for path in paths:
            if not path.is_file():
                continue
            parts.append(ContextPart(f"skill:{skill_name}/{path.relative_to(skill_dir)}", path.read_text(encoding="utf-8")))
    return parts


def _parts_for_stage(stage: str, args: argparse.Namespace) -> list[ContextPart]:
    from app.agents import hitl_agents

    skills_dir = Path(hitl_agents.__file__).resolve().parent.parent / "skills"
    if stage == "classifier":
        return [ContextPart("system:classifier", hitl_agents.CLASSIFIER_SYSTEM_PROMPT)]

    if stage == "composer":
        parts = [
            ContextPart("system:composer", hitl_agents.COMPOSER_SYSTEM_PROMPT),
            ContextPart("tier1:composer", hitl_agents.get_composer_tier1_preinjected_context(args.mode)),
            ContextPart("user:composer", _composer_prompt(args)),
        ]
        return parts + _skill_files(
            ("manim-composer", "manimce-best-practices"),
            skills_dir,
            include_all_files=args.include_all_skill_files,
        )

    if stage == "coder":
        parts = [
            ContextPart("system:coder", hitl_agents.CODER_SYSTEM_PROMPT),
            ContextPart("tier1:coder", _coder_context(args, hitl_agents)),
            ContextPart("user:coder", _coder_prompt(args)),
        ]
        return parts + _skill_files(
            ("manimce-best-practices", "manim-render"),
            skills_dir,
            include_all_files=args.include_all_skill_files,
        )

    if stage == "repair":
        parts = [
            ContextPart("system:repair", hitl_agents.REPAIR_SYSTEM_PROMPT),
            ContextPart("user:repair", _repair_prompt(args)),
        ]
        return parts + _skill_files(
            ("manimce-best-practices", "manim-render"),
            skills_dir,
            include_all_files=args.include_all_skill_files,
        )

    raise ValueError(f"Unsupported stage: {stage}")


def _composer_prompt(args: argparse.Namespace) -> str:
    subject_line = f"Subject Domain: {args.subject}\n" if args.subject else ""
    return (
        f"Educational Content to visualize:\n{args.text}\n\n"
        f"Topic: {args.topic}\n{subject_line}\n"
        "Using both the manim-composer and manimce-best-practices skills as your guide, "
        "compose a comprehensive scenes.md visual plan."
    )


def _coder_context(args: argparse.Namespace, hitl_agents: object) -> str:
    if args.mode == "slide":
        return hitl_agents.get_slide_tier1_context()
    if args.mode == "scivis":
        return hitl_agents.get_scivis_tier1_context(needs_3d=args.needs_3d)
    if args.mode == "marp":
        return hitl_agents.get_marp_tier1_context()
    return hitl_agents.get_animation_tier1_context(needs_3d=args.needs_3d)


def _coder_prompt(args: argparse.Namespace) -> str:
    mode_guideline = {
        "animation": "Emphasize fluid motion, relative positioning, updaters, and seamless transforms.",
        "slide": "Use distinct slides, VGroups, FadeOut transitions, and clear pauses; avoid continuous updaters.",
        "scivis": "Define get_data() before the Scene class and map scientific data to Manim primitives with fallbacks.",
        "marp": "Follow the title, bullets, two-col, code-focus, math-focus, and quote layout vocabulary.",
    }[args.mode]
    return (
        f"Topic: {args.topic}\n\nMode: {args.mode.upper()}\n\n"
        f"Approved scenes.md Visual Plan:\n{args.text}\n\n"
        f"Mode guideline: {mode_guideline}\n\n"
        "Synthesize a complete production-quality Manim Community Edition Python scene and return only code."
    )


def _repair_prompt(args: argparse.Namespace) -> str:
    return f"Repair this Manim code.\n\nError:\n{args.error}\n\nCurrent code:\n{args.code}"


def _print_report(
    stage: str,
    parts: list[ContextPart],
    count_tokens: Callable[[str], int],
    max_output_tokens: int,
) -> None:
    rows = [(part.name, count_tokens(part.text), len(part.text)) for part in parts]
    total = sum(tokens for _, tokens, _ in rows)
    context_total = total + max_output_tokens
    remaining = CONTEXT_WINDOW - context_total
    print(f"Stage: {stage} (max output: {max_output_tokens:,} tokens)")
    print(f"Context window: {CONTEXT_WINDOW:,} tokens")
    print(f"Estimated input tokens: {total:,}")
    print(f"Input + max output: {context_total:,} tokens")
    print(f"Remaining context capacity: {remaining:,} tokens")
    print(f"Status: {'OVER BUDGET' if remaining < 0 else 'within budget'}")
    print("\nBreakdown:")
    for name, tokens, chars in sorted(rows, key=lambda row: row[1], reverse=True):
        print(f"  {tokens:>7,} tokens  {chars:>8,} chars  {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("classifier", "composer", "coder", "repair", "all"), default="all")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Tokenizer model name; unknown models use cl100k_base")
    parser.add_argument("--text", default="Fourier Transform", help="Educational text, plan, or code input")
    parser.add_argument("--topic", default="Fourier Transform")
    parser.add_argument("--subject", default="math")
    parser.add_argument("--mode", choices=("animation", "slide", "scivis", "marp"), default="animation")
    parser.add_argument("--error", default="SyntaxError: invalid syntax")
    parser.add_argument("--code", default="from manim import *\n\nclass GeneratedScene(Scene):\n    def construct(self):\n        pass")
    parser.add_argument("--needs-3d", action="store_true")
    parser.add_argument(
        "--include-all-skill-files",
        action="store_true",
        help="Also count every local skill reference file (worst-case; tier-1 rules may overlap)",
    )
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parents[1]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    count_tokens = _load_tokenizer(args.model)
    stages = ("classifier", "composer", "coder", "repair") if args.stage == "all" else (args.stage,)
    from app.agents import hitl_agents

    for index, stage in enumerate(stages):
        if index:
            print("\n" + "=" * 72 + "\n")
        max_output_tokens = min(4096, hitl_agents.HITL_MAX_TOKENS) if stage == "classifier" else hitl_agents.HITL_MAX_TOKENS
        _print_report(stage, _parts_for_stage(stage, args), count_tokens, max_output_tokens)


if __name__ == "__main__":
    main()
