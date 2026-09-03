#!/usr/bin/env python3
"""Populate missing metadata fields for all problem bundles in apps/grpo_dataset using LLM synthesis.

Uses gemini-3.5-flash via inference.net OpenAI-compatible endpoint to generate:
- problem.json
- visual_events.json
- coverage.json
- version_notes.json
- ref_embeddings.npy
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

SCRIPT_DIR = Path(__file__).resolve().parent
GRPO_ROOT = SCRIPT_DIR.parent
REPO_ROOT = GRPO_ROOT.parent.parent
DATA_DIR = GRPO_ROOT / "data"
PROBLEMS_DIR = DATA_DIR / "problems"
CURATED_PATH = SCRIPT_DIR / "curated_scenes.json"

DEFAULT_BASE_URL = "https://api.inference.net/v1"
DEFAULT_MODEL_ID = "gemini-3.5-flash"


def init_environment() -> None:
    """Load environment variables from .env files."""
    if load_dotenv:
        for env_path in (
            REPO_ROOT / ".env",
            GRPO_ROOT.parent / "sft" / ".env",
            GRPO_ROOT.parent / "agents" / ".env",
            GRPO_ROOT / ".env",
            Path.cwd() / ".env",
        ):
            if env_path.is_file():
                load_dotenv(env_path, override=False)


SYSTEM_PROMPT = """You are an expert Manim and ManimGL visualization engineer and dataset curator.
Given reference Python code and metadata for a Manim scene, generate 4 complete JSON metadata objects:
1. `problem.json`
2. `visual_events.json`
3. `coverage.json`
4. `version_notes.json`

CRITICAL RULES:
1. Output format: Return a SINGLE JSON object containing top-level keys `"problem"`, `"visual_events"`, `"coverage"`, and `"version_notes"`.
2. `"problem"` fields:
   - `id`: exact problem ID (e.g. "MB-001")
   - `title`: descriptive human-readable title
   - `youtube_video_id`: string (or empty "")
   - `video_timestamp_range`: [start_sec, end_sec] (e.g. [0.0, 60.0])
   - `category`: array of strings from ["direct-visualization", "concept-exposition", "drift-sensitive", "interactive", "geometric-derivation"]
   - `difficulty_level`: integer 1 to 5
   - `domain`: array of strings e.g. ["Calculus", "ML", "Linear Algebra", "Physics", "Computer Science"]
   - `full_prompt`: A detailed, self-contained prompt instructing an AI agent to build this exact visualization.
   - `raw_code_status`: "collected"
   - `raw_code_path`: "data/problems/<ID>/reference.py"
   - `reference_code_analysis`: object with `framework`, `total_lines`, `scene_classes`, `visual_techniques`, `manim_api_patterns`
   - `required_visual_events_path`: "visual_events.json"
   - `coverage_requirements_path`: "coverage.json"
   - `version_conflict_notes_path`: "version_notes.json"
   - `reference_embeddings_path`: "ref_embeddings.npy"
   - `success_criteria`: {"min_executability": 1.0, "min_alignment": 0.7, "min_coverage": 0.5, "max_vcer": 0.0}
   - `common_failure_modes`: array of {"pattern": "...", "severity": "high"|"medium"|"low", "note": "..."}

3. `"visual_events"` fields:
   - `problem_id`: exact problem ID
   - `events`: array of 3 to 5 events, each with:
     - `event_id`: e.g. "ev_01", "ev_02"
     - `description`: clear visual event description
     - `weight`: float (MUST sum to 1.0 across all events)
     - `critical`: boolean
     - `expected_time_range`: [t_start, t_end]
     - `keyword_bank`: array of string keywords/Mobject names expected in code
     - `clip_query`: concise natural language string for CLIP frame matching

4. `"coverage"` fields:
   - `problem_id`: exact problem ID
   - `requirements`: object with keys `"Math"`, `"Visual"`, `"Numeric"`, `"Structural"`.
     Each key has `{"weight": float, "expected": [string, ...]}`.
     The 4 category weights MUST sum to 1.0.

5. `"version_notes"` fields:
   - `problem_id`: exact problem ID
   - `conflicts`: array of {"category": "...", "gl_construct": "...", "ce_equivalent": "...", "severity": "..."}

Return ONLY valid JSON matching this schema inside a single ```json code block. No additional markdown prose."""


def normalize_event_weights(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensure visual event weights sum to 1.0 exactly."""
    if not events:
        return events
    total = sum(float(e.get("weight", 0.0)) for e in events)
    if total <= 0:
        equal_w = round(1.0 / len(events), 4)
        for e in events:
            e["weight"] = equal_w
        events[-1]["weight"] = round(1.0 - sum(e["weight"] for e in events[:-1]), 4)
    else:
        for e in events:
            e["weight"] = round(float(e["weight"]) / total, 4)
        rem = round(1.0 - sum(e["weight"] for e in events[:-1]), 4)
        events[-1]["weight"] = rem
    return events


def normalize_coverage_weights(requirements: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure coverage requirement category weights sum to 1.0 exactly."""
    if not requirements:
        return requirements
    keys = list(requirements.keys())
    total = sum(float(requirements[k].get("weight", 0.0)) for k in keys)
    if total <= 0:
        equal_w = round(1.0 / len(keys), 4)
        for k in keys:
            requirements[k]["weight"] = equal_w
        requirements[keys[-1]]["weight"] = round(1.0 - sum(requirements[k]["weight"] for k in keys[:-1]), 4)
    else:
        for k in keys:
            requirements[k]["weight"] = round(float(requirements[k]["weight"]) / total, 4)
        rem = round(1.0 - sum(requirements[k]["weight"] for k in keys[:-1]), 4)
        requirements[keys[-1]]["weight"] = rem
    return requirements


def ensure_ref_embeddings(problem_dir: Path) -> None:
    """Generate dummy ref_embeddings.npy if not present."""
    emb_path = problem_dir / "ref_embeddings.npy"
    if not emb_path.exists() or emb_path.stat().st_size == 0:
        # Generate reproducible pseudo-random embeddings (5 x 512)
        seed = sum(ord(c) for c in problem_dir.name)
        rng = np.random.RandomState(seed)
        mat = rng.randn(5, 512).astype(np.float32)
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        mat = mat / np.maximum(norms, 1e-8)
        np.save(emb_path, mat)


def is_problem_complete(problem_dir: Path) -> bool:
    """Check if problem directory contains all valid, non-empty metadata files."""
    pid = problem_dir.name
    required = [
        "problem.json",
        "reference.py",
        "visual_events.json",
        "coverage.json",
        "version_notes.json",
        "ref_embeddings.npy",
    ]
    for req in required:
        f = problem_dir / req
        if not f.exists() or f.stat().st_size == 0:
            return False

    try:
        pjson = json.loads((problem_dir / "problem.json").read_text(encoding="utf-8"))
        vevents = json.loads((problem_dir / "visual_events.json").read_text(encoding="utf-8"))
        cov = json.loads((problem_dir / "coverage.json").read_text(encoding="utf-8"))
        vnotes = json.loads((problem_dir / "version_notes.json").read_text(encoding="utf-8"))

        if pjson.get("id") != pid:
            return False
        if vevents.get("problem_id") != pid or not vevents.get("events"):
            return False
        if cov.get("problem_id") != pid or not cov.get("requirements"):
            return False
        if vnotes.get("problem_id") != pid:
            return False

        # Validate weight sums
        e_weights = [float(e.get("weight", 0.0)) for e in vevents.get("events", [])]
        if not math.isclose(sum(e_weights), 1.0, rel_tol=1e-3, abs_tol=1e-3):
            return False

        c_weights = [float(spec.get("weight", 0.0)) for spec in cov.get("requirements", {}).values()]
        if not math.isclose(sum(c_weights), 1.0, rel_tol=1e-3, abs_tol=1e-3):
            return False

        return True
    except (json.JSONDecodeError, KeyError, Exception):
        return False


async def populate_single_problem(
    client: AsyncOpenAI,
    model_id: str,
    problem_dir: Path,
    curated_info: Optional[Dict[str, Any]],
    semaphore: asyncio.Semaphore,
    max_retries: int = 4,
) -> bool:
    """Populate metadata for a single problem folder via LLM synthesis."""
    pid = problem_dir.name
    ref_py = problem_dir / "reference.py"
    ref_code = ref_py.read_text(encoding="utf-8", errors="replace") if ref_py.exists() else ""

    info_str = f"Problem ID: {pid}\n"
    if curated_info:
        info_str += f"Class Name: {curated_info.get('class_name')}\n"
        info_str += f"Topic: {curated_info.get('topic')}\n"
        info_str += f"Year: {curated_info.get('year')}\n"

    prompt_content = (
        f"{info_str}\n"
        f"Reference Code snippet (first 150 lines):\n"
        f"```python\n{ref_code[:4000]}\n```\n\n"
        f"Generate the combined metadata JSON object for {pid}."
    )

    async with semaphore:
        for attempt in range(1, max_retries + 1):
            try:
                completion = await client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt_content},
                    ],
                    temperature=0.2,
                    max_tokens=4096,
                )
                raw_text = completion.choices[0].message.content or ""
                match = re.search(r"```json\s*(.*?)\s*```", raw_text, re.DOTALL)
                clean_text = match.group(1).strip() if match else raw_text.strip()
                data = json.loads(clean_text)

                pjson = data.get("problem", {})
                vevents = data.get("visual_events", {})
                cov = data.get("coverage", {})
                vnotes = data.get("version_notes", {})

                # Ensure IDs match
                pjson["id"] = pid
                vevents["problem_id"] = pid
                cov["problem_id"] = pid
                vnotes["problem_id"] = pid

                # Fix path references in problem.json
                pjson["raw_code_status"] = "collected"
                pjson["raw_code_path"] = f"data/problems/{pid}/reference.py"
                pjson["required_visual_events_path"] = "visual_events.json"
                pjson["coverage_requirements_path"] = "coverage.json"
                pjson["version_conflict_notes_path"] = "version_notes.json"
                pjson["reference_embeddings_path"] = "ref_embeddings.npy"

                # Normalize weights
                if "events" in vevents:
                    vevents["events"] = normalize_event_weights(vevents["events"])
                if "requirements" in cov:
                    cov["requirements"] = normalize_coverage_weights(cov["requirements"])

                # Write JSON files
                (problem_dir / "problem.json").write_text(json.dumps(pjson, indent=2) + "\n", encoding="utf-8")
                (problem_dir / "visual_events.json").write_text(json.dumps(vevents, indent=2) + "\n", encoding="utf-8")
                (problem_dir / "coverage.json").write_text(json.dumps(cov, indent=2) + "\n", encoding="utf-8")
                (problem_dir / "version_notes.json").write_text(json.dumps(vnotes, indent=2) + "\n", encoding="utf-8")

                ensure_ref_embeddings(problem_dir)

                return True
            except Exception as exc:
                err_str = str(exc)
                if "429" in err_str or "rate limit" in err_str.lower():
                    wait_s = 2**attempt + 2
                    print(f"  [429 Rate Limit] {pid}, retrying in {wait_s}s...")
                    await asyncio.sleep(wait_s)
                else:
                    print(f"  [Error] {pid} attempt {attempt}/{max_retries}: {err_str[:120]}")
                    if attempt == max_retries:
                        return False
                    await asyncio.sleep(2)

    return False


async def run_population_pipeline(
    api_key: str,
    base_url: str,
    model_id: str,
    concurrency: int = 5,
    force: bool = False,
) -> None:
    """Run parallel population across all problem directories."""
    if AsyncOpenAI is None:
        raise ImportError("openai package required (`uv add openai`).")

    client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    curated_map: Dict[str, Dict[str, Any]] = {}
    if CURATED_PATH.is_file():
        try:
            items = json.loads(CURATED_PATH.read_text(encoding="utf-8"))
            for item in items:
                curated_map[item["id"]] = item
        except Exception:
            pass

    problems = sorted(list(PROBLEMS_DIR.glob("*/")))
    print(f"Targeting {len(problems)} problem directories in {PROBLEMS_DIR}")

    # Fix weight normalization for existing populated folders first
    fixed_existing = 0
    for problem_dir in problems:
        pid = problem_dir.name
        ensure_ref_embeddings(problem_dir)
        vevents_f = problem_dir / "visual_events.json"
        cov_f = problem_dir / "coverage.json"
        if vevents_f.exists() and vevents_f.stat().st_size > 0:
            try:
                vevents = json.loads(vevents_f.read_text(encoding="utf-8"))
                if "events" in vevents and vevents.get("events"):
                    vevents["events"] = normalize_event_weights(vevents["events"])
                    vevents_f.write_text(json.dumps(vevents, indent=2) + "\n", encoding="utf-8")
                    fixed_existing += 1
            except Exception:
                pass
        if cov_f.exists() and cov_f.stat().st_size > 0:
            try:
                cov = json.loads(cov_f.read_text(encoding="utf-8"))
                if "requirements" in cov and cov.get("requirements"):
                    cov["requirements"] = normalize_coverage_weights(cov["requirements"])
                    cov_f.write_text(json.dumps(cov, indent=2) + "\n", encoding="utf-8")
            except Exception:
                pass

    if fixed_existing > 0:
        print(f"Pre-processed and normalized weights for existing populated problem files.")

    to_process = []
    for problem_dir in problems:
        if force or not is_problem_complete(problem_dir):
            to_process.append(problem_dir)

    print(f"Problems remaining to populate: {len(to_process)} / {len(problems)}")
    if not to_process:
        print("All problem directories are already complete and valid!")
        return

    semaphore = asyncio.Semaphore(concurrency)
    completed_count = len(problems) - len(to_process)

    async def worker(problem_dir: Path) -> None:
        nonlocal completed_count
        pid = problem_dir.name
        curated_info = curated_map.get(pid)
        success = await populate_single_problem(
            client=client,
            model_id=model_id,
            problem_dir=problem_dir,
            curated_info=curated_info,
            semaphore=semaphore,
        )
        completed_count += 1
        status_str = "SUCCESS" if success else "FAILED"
        print(f"[{completed_count}/{len(problems)}] {pid}: {status_str}")

    tasks = [worker(p) for p in to_process]
    await asyncio.gather(*tasks)

    print("\nMetadata population completed!")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Populate GRPO dataset metadata using LLM API")
    parser.add_argument(
        "--base-url",
        default=os.getenv("INFERENCE_NET_BASE_URL", DEFAULT_BASE_URL),
        help=f"OpenAI-compatible base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--model-id",
        default=DEFAULT_MODEL_ID,
        help=f"Model ID (default: {DEFAULT_MODEL_ID})",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("INFERENCE_NET_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY", ""),
        help="API Key",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Number of concurrent API requests (default: 5)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-generate metadata even if problem is already complete",
    )
    return parser


def main() -> int:
    init_environment()
    args = build_arg_parser().parse_args()
    api_key = (
        args.api_key
        or os.getenv("INFERENCE_NET_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("GEMINI_API_KEY", "")
    ).strip()

    if not api_key:
        print("ERROR: Set INFERENCE_NET_API_KEY or OPENAI_API_KEY in environment or .env file.", file=sys.stderr)
        return 1

    try:
        asyncio.run(
            run_population_pipeline(
                api_key=api_key,
                base_url=args.base_url,
                model_id=args.model_id,
                concurrency=args.concurrency,
                force=args.force,
            )
        )
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
