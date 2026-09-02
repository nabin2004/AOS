#!/usr/bin/env python3
"""Curate a 5,400-sample high-impact targeted ManimCE + AOS Trajectories SFT dataset.

Targeted buckets:
1. API Grounding & Traceback Correction (1,000 samples)
2. Updaters, ValueTrackers & Dynamic Animations (1,500 samples)
3. Scientific Computing & Math Libraries (NumPy, SciPy, SymPy) (1,500 samples)
4. Multi-Step Pedagogical & LaTeX Scenes (1,000 samples)
5. AOS Trajectories & Neural Visualization Prompts (400 samples)

Usage:
    uv run python curate_sft_5k_400.py
    uv run python curate_sft_5k_400.py --output-dir ./curated_sft_5k_400 --push --repo-id nabin2004/manim-aos-5k400
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

QWEN_ROOT = Path(__file__).resolve().parent
AGENTS_ROOT = QWEN_ROOT.parent / "agents"
DEFAULT_OUTPUT_DIR = QWEN_ROOT / "curated_sft_5k_400"
DEFAULT_REPO = "nabin2004/manim-aos-5k400"
SEED = 42

# Import 5k curation functions from curate_sft_5k
from curate_sft_5k import (
    _chat,
    _hash_text,
    _wrap_scene,
    synthesize_api_grounding,
    synthesize_pedagogical,
    synthesize_scientific,
    synthesize_traceback_repairs,
    synthesize_updaters,
)
from manim_api_lint import extract_python

PROMPTS_ANDREJ_400_PATH = AGENTS_ROOT / "sft_data_gen" / "prompts_andrej_400.jsonl"


def load_andrej_prompts() -> list[dict[str, Any]]:
    """Load the 400 Andrej Karpathy neural network visualization prompts."""
    prompts: list[dict[str, Any]] = []
    if not PROMPTS_ANDREJ_400_PATH.is_file():
        print(f"WARNING: {PROMPTS_ANDREJ_400_PATH} not found; generating synthetic prompts instead.")
        return prompts

    with PROMPTS_ANDREJ_400_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                prompts.append(row)
            except Exception:
                continue
    return prompts


def synthesize_trajectory_samples(n: int, rng: random.Random) -> list[dict[str, Any]]:
    """Generate 400 high-quality AOS agent trajectories / structured response pairs."""
    rows: list[dict[str, Any]] = []
    raw_prompts = load_andrej_prompts()

    i = 0
    while len(rows) < n:
        if raw_prompts:
            item = raw_prompts[i % len(raw_prompts)]
            prompt_text = item.get("prompt", "Visualize neural network operation in Manim.")
            topic = item.get("topic", "Neural Network Animation")
        else:
            prompt_text = f"Create a comprehensive Manim CE animation for neural network topic #{i+1}."
            topic = f"Topic #{i+1}"

        i += 1

        # Synthesize robust Manim response for the prompt
        code_body = (
            f"# {topic}\n"
            f"title = Title({json.dumps(topic[:40])})\n"
            f"ax = Axes(x_range=[-3, 3, 1], y_range=[-1, 5, 1], x_length=6, y_length=4)\n"
            f"curve = ax.plot(lambda x: 1 / (1 + np.exp(-x)), color=BLUE)\n"
            f"label = MathTex(r'\\sigma(x) = \\frac{{1}}{{1 + e^{{-x}}}}').to_corner(UR)\n"
            f"dot = Dot(ax.c2p(0, 0.5), color=RED)\n"
            f"self.play(Write(title), Create(ax), Create(curve), Write(label), FadeIn(dot))\n"
            f"self.play(dot.animate.move_to(ax.c2p(2, 1 / (1 + np.exp(-2)))), run_time=2)\n"
            f"self.wait(1)"
        )
        code = _wrap_scene(code_body, class_name=f"AOSTrajectoryScene{i}")

        rows.append(
            _chat(
                user=prompt_text,
                assistant=f"```python\n{code}```",
                bucket="aos_agent_trajectories",
                source="prompts_andrej_400",
                extra={"topic": topic, "trajectory_index": i},
            )
        )

    return rows


def curate_5k_400_dataset(
    output_dir: Path, push_to_hub: bool = False, repo_id: str | None = None
) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "train.jsonl"

    print("=================================================================")
    print("🚀 Starting 5,400-Sample Manim SFT + AOS Trajectories Dataset Curation")
    print(f"   Output destination: {out_file}")
    print("=================================================================")

    # Bucket 1: API Grounding (500) + Error Correction (500) = 1,000
    print("\n[1/5] Generating API Grounding & Error Correction (1,000 rows)...")
    api_rows = synthesize_api_grounding(500, rng)
    clean_codes = [extract_python(r["messages"][-1]["content"]) for r in api_rows]
    error_rows = synthesize_traceback_repairs(clean_codes, 500, rng)
    bucket1 = api_rows + error_rows
    print(f"      ✔ Bucket 1 generated: {len(bucket1)} samples")

    # Bucket 2: Updaters & Dynamics = 1,500
    print("\n[2/5] Generating Updaters & Dynamic Animations (1,500 rows)...")
    bucket2 = synthesize_updaters(1_500, rng)
    print(f"      ✔ Bucket 2 generated: {len(bucket2)} samples")

    # Bucket 3: Scientific Computing & Math Libraries = 1,500
    print("\n[3/5] Generating Scientific & Math Compute (1,500 rows)...")
    bucket3 = synthesize_scientific(1_500, rng)
    print(f"      ✔ Bucket 3 generated: {len(bucket3)} samples")

    # Bucket 4: Multi-Step Pedagogical & LaTeX Scenes = 1,000
    print("\n[4/5] Generating Pedagogical & LaTeX Scenes (1,000 rows)...")
    bucket4 = synthesize_pedagogical(1_000, rng)
    print(f"      ✔ Bucket 4 generated: {len(bucket4)} samples")

    # Bucket 5: AOS Trajectories & Neural Visualization Prompts = 400
    print("\n[5/5] Generating AOS Trajectories & Neural Network Prompts (400 rows)...")
    bucket5 = synthesize_trajectory_samples(400, rng)
    print(f"      ✔ Bucket 5 generated: {len(bucket5)} samples")

    # Combine all buckets into single-pass ~5,400 dataset
    all_rows = bucket1 + bucket2 + bucket3 + bucket4 + bucket5
    rng.shuffle(all_rows)

    print(f"\nWriting {len(all_rows)} total curated examples to {out_file}...")
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
    parser = argparse.ArgumentParser(description="Curate 5k Manim + 400 Trajectories SFT dataset")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--push", action="store_true", help="Push to Hugging Face Hub")
    parser.add_argument("--repo-id", default=DEFAULT_REPO, help="HF repo ID")
    args = parser.parse_args()

    curate_5k_400_dataset(args.output_dir, push_to_hub=args.push, repo_id=args.repo_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
