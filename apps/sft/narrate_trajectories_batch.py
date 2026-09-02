#!/usr/bin/env python3
"""Inference.net / OpenAI-compatible API pipeline for converting Manim trajectories to manim-voiceover.

Converts standard Manim trajectories into executable manim-voiceover scripts using
gemini-2.5-flash-lite via the inference.net OpenAI-compatible endpoint. Supports
concurrent async processing, streaming responses, and resume checkpointing.

Endpoint details:
    Base URL: https://api.inference.net/v1
    Model: gemini-2.5-flash-lite
    Key: INFERENCE_NET_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY

Usage:
    uv run python narrate_trajectories_batch.py
    uv run python narrate_trajectories_batch.py --concurrency 8
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

SFT_ROOT = Path(__file__).resolve().parent
AGENTS_ROOT = SFT_ROOT.parent / "agents"
REPO_ROOT = SFT_ROOT.parent.parent
QWEN_400_TRAJECTORIES = SFT_ROOT.parent / "qwenCoder" / "curated_sft_5k_400" / "train.jsonl"
DEFAULT_INPUT_TRAJECTORIES = (
    QWEN_400_TRAJECTORIES
    if QWEN_400_TRAJECTORIES.is_file()
    else AGENTS_ROOT / "training_data" / "trajectories.jsonl"
)
DEFAULT_OUTPUT_DIR = SFT_ROOT / "dataset_narrated"
DEFAULT_BASE_URL = "https://api.inference.net/v1"
DEFAULT_MODEL_ID = "gemini-2.5-flash-lite"


def init_environment() -> None:
    """Auto-load environment variables from .env files in sft, agents, or repo root."""
    if load_dotenv:
        for env_path in (
            REPO_ROOT / ".env",
            AGENTS_ROOT / ".env",
            SFT_ROOT / ".env",
            Path.cwd() / ".env",
        ):
            if env_path.is_file():
                load_dotenv(env_path, override=False)


SYSTEM_INSTRUCTION = """You are an expert Manim and manim-voiceover engineer.
Convert the provided standard Manim CE Python code into an executable manim-voiceover script using fine-grained voiceover narration and bookmark synchronization.

CRITICAL RULES:
1. Imports: Replace or augment imports with:
   from manim import *
   from manim_voiceover import VoiceoverScene
   from tools.aos_speech_service import AOSSpeechService
2. Class Definition: Inherit strictly from VoiceoverScene (never Scene).
3. Setup: Call `self.set_speech_service(AOSSpeechService(voice="alba", cache_dir="voiceover_cache"))` as the first line of construct().
4. Voiceover Wrapping & Fine-Grained Bookmarks:
   - Wrap visual animations inside `with self.voiceover(text="...") as tracker:` blocks.
   - Use `<bookmark mark='MARK_NAME'/>` tags inside the narration text at major visual transition points (e.g. before showing a formula, creating axes, moving a dot, or revealing a title).
   - Inside the `with self.voiceover(...)` block, call `self.wait_until_bookmark("MARK_NAME")` before playing the corresponding animation so visual actions trigger mid-narration exactly when spoken.
   - For continuous or end-of-speech animations, use `run_time=tracker.duration`.
5. Voiceover Text Guidelines:
   - Voiceover text must explain mathematical intuition and high-level concepts, NOT describe literal code variable names or operations.
   - NEVER put raw LaTeX commands (\\frac, \\sqrt, \\int), underscores, or syntax symbols inside voiceover strings. Spell them out phonetically (e.g., "the integral of x squared", "divided by two", "sigma of x").
6. Geometric Preservation: Do NOT alter coordinates, math transformations, colors, or object logic from the original code.

EXAMPLE PATTERN WITH BOOKMARKS:
```python
from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService

class MyNarratedScene(VoiceoverScene):
    def construct(self):
        self.set_speech_service(AOSSpeechService(voice="alba", cache_dir="voiceover_cache"))
        
        title = Title("Sigmoid Function")
        ax = Axes(x_range=[-3, 3, 1], y_range=[-1, 5, 1])
        curve = ax.plot(lambda x: 1 / (1 + np.exp(-x)), color=BLUE)
        
        with self.voiceover(
            text="Let us begin by creating our coordinate axes <bookmark mark='SHOW_CURVE'/> and then plotting the sigmoid activation curve."
        ) as tracker:
            self.play(Write(title), Create(ax))
            self.wait_until_bookmark("SHOW_CURVE")
            self.play(Create(curve), run_time=tracker.duration)
```

7. Output: Return ONLY executable Python code inside a single ```python code block. No explanations, no markdown outside the code block."""



def _extract_code(data: Dict[str, Any]) -> Optional[str]:
    """Extract Python code from various trajectory schema representations."""
    for key in ("code", "solution", "final_code", "source", "manim_code"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()

    # Check messages array (OpenAI / ShareGPT chat format)
    messages = data.get("messages") or []
    if isinstance(messages, list):
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                content = msg.get("content", "")
                if isinstance(content, str):
                    match = re.search(r"```python\s*(.*?)\s*```", content, re.DOTALL)
                    if match:
                        return match.group(1).strip()
                    if "class " in content and "Scene" in content:
                        return content.strip()

    # Fallback: check nested trajectory steps
    trajectory = data.get("trajectory") or data.get("steps") or []
    if isinstance(trajectory, list):
        for step in reversed(trajectory):
            if isinstance(step, dict):
                code = _extract_code(step)
                if code:
                    return code

    return None


async def _convert_single_item(
    client: AsyncOpenAI,
    model_id: str,
    item_id: str,
    code: str,
    semaphore: asyncio.Semaphore,
    stream: bool = True,
    max_retries: int = 5,
) -> Dict[str, Any]:
    """Convert a single Manim script to voiceover format with retry backoff."""
    prompt_content = f"Original Manim Code:\n```python\n{code}\n```"

    async with semaphore:
        for attempt in range(1, max_retries + 1):
            try:
                if stream:
                    completion = await client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": SYSTEM_INSTRUCTION},
                            {"role": "user", "content": prompt_content},
                        ],
                        temperature=0.2,
                        max_tokens=4096,
                        stream=True,
                    )
                    chunks = []
                    async for chunk in completion:
                        if chunk.choices and chunk.choices[0].delta.content:
                            chunks.append(chunk.choices[0].delta.content)
                    raw_text = "".join(chunks)
                else:
                    completion = await client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": SYSTEM_INSTRUCTION},
                            {"role": "user", "content": prompt_content},
                        ],
                        temperature=0.2,
                        max_tokens=4096,
                        stream=False,
                    )
                    raw_text = completion.choices[0].message.content or ""

                match = re.search(r"```python\s*(.*?)\s*```", raw_text, re.DOTALL)
                clean_code = match.group(1).strip() if match else raw_text.strip()
                return {
                    "id": item_id,
                    "narrated_manim_code": clean_code,
                    "status": "success",
                }
            except Exception as exc:
                err_str = str(exc)
                if "429" in err_str or "rate limit" in err_str.lower():
                    wait_time = 2**attempt + 2
                    print(f"  [429 Rate Limit] {item_id}, retrying in {wait_time}s (attempt {attempt}/{max_retries})...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"  [Error] {item_id}: {err_str[:120]} (attempt {attempt}/{max_retries})")
                    if attempt == max_retries:
                        return {
                            "id": item_id,
                            "error": err_str,
                            "status": "failed",
                        }
                    await asyncio.sleep(2)

    return {"id": item_id, "error": "Max retries exceeded", "status": "failed"}


async def run_direct_conversion(
    api_key: str,
    base_url: str,
    model_id: str,
    input_path: Path,
    output_dir: Path,
    concurrency: int = 5,
    only_andrej_400: bool = True,
    stream: bool = True,
) -> Path:
    """Convert trajectories directly via asynchronous parallel requests with resume checkpointing."""
    if AsyncOpenAI is None:
        raise ImportError(
            "The 'openai' package is required. Install with `uv add openai`."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    final_dataset_file = output_dir / "manim_narrated_400.jsonl"

    client = AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
    )

    # 1. Load existing results for resume capability
    completed_ids: Set[str] = set()
    if final_dataset_file.is_file():
        with open(final_dataset_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        if record.get("status") == "success":
                            completed_ids.add(record.get("id"))
                    except json.JSONDecodeError:
                        continue
        if completed_ids:
            print(f"Resume Checkpoint: Found {len(completed_ids)} already converted items in {final_dataset_file.name}")

    # 2. Collect items to convert
    tasks_to_run = []
    with open(input_path, "r", encoding="utf-8") as infile:
        for idx, line in enumerate(infile):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            metadata = data.get("metadata", {})
            source = metadata.get("source", "")
            if only_andrej_400 and source and source != "prompts_andrej_400":
                continue

            code = _extract_code(data)
            if not code:
                continue

            item_id = f"sample_{idx}"
            if item_id in completed_ids:
                continue

            tasks_to_run.append((item_id, code))

    total_remaining = len(tasks_to_run)
    total_dataset = len(completed_ids) + total_remaining
    print(f"Targeting {total_dataset} trajectories total ({total_remaining} remaining to convert).")
    print(f"Using endpoint: {base_url} | Model: {model_id} | Concurrency: {concurrency}")

    if total_remaining == 0:
        print(f"All items already completed in: {final_dataset_file}")
        return final_dataset_file

    semaphore = asyncio.Semaphore(concurrency)
    write_lock = asyncio.Lock()
    completed_count = len(completed_ids)

    async def worker(item_id: str, code: str) -> None:
        nonlocal completed_count
        result = await _convert_single_item(
            client=client,
            model_id=model_id,
            item_id=item_id,
            code=code,
            semaphore=semaphore,
            stream=stream,
        )
        async with write_lock:
            with open(final_dataset_file, "a", encoding="utf-8") as out:
                out.write(json.dumps(result) + "\n")
            completed_count += 1
            status_str = result.get("status", "unknown")
            print(f"[{completed_count}/{total_dataset}] {item_id}: {status_str}")

    tasks = [worker(item_id, code) for item_id, code in tasks_to_run]
    await asyncio.gather(*tasks)

    print(f"\nNarration conversion completed! Saved to: {final_dataset_file}")
    return final_dataset_file


def run_conversion(
    api_key: str,
    model_id: str = DEFAULT_MODEL_ID,
    base_url: str = DEFAULT_BASE_URL,
    input_path: Path = DEFAULT_INPUT_TRAJECTORIES,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    concurrency: int = 5,
    stream: bool = True,
    **kwargs,
) -> Path:
    """Run narration conversion via inference.net endpoint."""
    return asyncio.run(
        run_direct_conversion(
            api_key=api_key,
            base_url=base_url,
            model_id=model_id,
            input_path=input_path,
            output_dir=output_dir,
            concurrency=concurrency,
            stream=stream,
        )
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert Manim trajectory dataset to manim-voiceover scripts using inference.net (gemini-2.5-flash-lite)"
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        default=DEFAULT_INPUT_TRAJECTORIES,
        help=f"Path to input trajectories JSONL (default: {DEFAULT_INPUT_TRAJECTORIES})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
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
        help="API Key (default: loaded from INFERENCE_NET_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY / .env)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Number of concurrent API requests (default: 5)",
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Disable streaming mode",
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
        run_conversion(
            api_key=api_key,
            base_url=args.base_url,
            model_id=args.model_id,
            input_path=args.input_path.resolve(),
            output_dir=args.output_dir.resolve(),
            concurrency=args.concurrency,
            stream=not args.no_stream,
        )
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
