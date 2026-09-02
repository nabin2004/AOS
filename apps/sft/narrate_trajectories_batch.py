#!/usr/bin/env python3
"""Gemini 2.5 Flash Batch & Direct API pipeline for converting Manim scripts to manim-voiceover.

Converts standard Manim trajectories into executable manim-voiceover scripts using
Gemini 2.5 Flash. Supports both asynchronous Batch API (50% token discount) and
direct concurrent async conversion with automatic fallback and resume checkpointing.

Usage:
    uv run python narrate_trajectories_batch.py
    uv run python narrate_trajectories_batch.py --mode direct --concurrency 5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from google import genai
    from google.genai import errors, types
except ImportError:
    genai = None
    errors = None
    types = None

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
DEFAULT_MODEL_ID = "gemini-2.5-flash"


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
Convert the provided standard Manim CE Python code into an executable manim-voiceover script.

CRITICAL RULES:
1. Imports: Replace or augment imports with:
   from manim import *
   from manim_voiceover import VoiceoverScene
   from manim_voiceover.services.gtts import GTTSService
2. Class Definition: Inherit strictly from VoiceoverScene (never Scene).
3. Setup: Call `self.set_speech_service(GTTSService())` as the first line of construct().
4. Voiceover Wrapping: Wrap visual animations inside `with self.voiceover(text="...") as tracker:` blocks. Use `run_time=tracker.duration` when synchronizing animations to spoken audio.
5. Voiceover Text Guidelines:
   - Voiceover text must explain mathematical intuition, not describe literal code operations.
   - NEVER put raw LaTeX commands (\\frac, \\sqrt, \\int), underscores, or symbols inside voiceover strings. Spell them out phonetically (e.g., "the integral of x squared", "divided by two").
6. Geometric Preservation: Do NOT alter coordinates, math transformations, colors, or object logic from the original code.
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


def prepare_batch_file(
    input_path: Path,
    batch_requests_file: Path,
    only_andrej_400: bool = True,
) -> int:
    """Read input trajectories and format batch requests JSONL file."""
    if not input_path.is_file():
        raise FileNotFoundError(f"Input trajectories file not found: {input_path}")

    count = 0
    with open(input_path, "r", encoding="utf-8") as infile, open(
        batch_requests_file, "w", encoding="utf-8"
    ) as outfile:
        for idx, line in enumerate(infile):
            line_str = line.strip()
            if not line_str:
                continue

            try:
                data = json.loads(line_str)
            except json.JSONDecodeError:
                continue

            metadata = data.get("metadata", {})
            source = metadata.get("source", "")
            # In mixed datasets like curated_sft_5k_400, isolate the 400 trajectories
            if only_andrej_400 and source and source != "prompts_andrej_400":
                continue

            code = _extract_code(data)
            if not code:
                continue

            sample_id = data.get("id") or data.get("user_prompt") or f"sample_{idx}"
            clean_key = f"sample_{idx}"
            prompt_content = f"Original Manim Code:\n```python\n{code}\n```"

            req = {
                "key": clean_key,
                "request": {
                    "system_instruction": {
                        "parts": [{"text": SYSTEM_INSTRUCTION}]
                    },
                    "contents": [{"parts": [{"text": prompt_content}]}],
                    "generation_config": {
                        "temperature": 0.2,
                        "max_output_tokens": 4096,
                    },
                },
                "metadata": {
                    "original_id": str(sample_id),
                    "prompt": data.get("user_prompt") or data.get("prompt") or "",
                },
            }
            outfile.write(json.dumps(req) + "\n")
            count += 1

    print(f"Prepared {count} batch requests in: {batch_requests_file}")
    return count


async def _convert_single_item(
    client: genai.Client,
    model_id: str,
    item_id: str,
    code: str,
    semaphore: asyncio.Semaphore,
    max_retries: int = 5,
) -> Dict[str, Any]:
    """Convert a single Manim script to voiceover format with retry backoff."""
    prompt_content = f"Original Manim Code:\n```python\n{code}\n```"
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.2,
        max_output_tokens=4096,
    )

    async with semaphore:
        for attempt in range(1, max_retries + 1):
            try:
                resp = await client.aio.models.generate_content(
                    model=model_id,
                    contents=prompt_content,
                    config=config,
                )
                raw_text = resp.text or ""
                match = re.search(r"```python\s*(.*?)\s*```", raw_text, re.DOTALL)
                clean_code = match.group(1).strip() if match else raw_text.strip()
                return {
                    "id": item_id,
                    "narrated_manim_code": clean_code,
                    "status": "success",
                }
            except Exception as exc:
                err_str = str(exc)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait_time = 2**attempt + 1
                    print(f"  Rate limit encountered for {item_id}, retrying in {wait_time}s (attempt {attempt}/{max_retries})...")
                    await asyncio.sleep(wait_time)
                else:
                    if attempt == max_retries:
                        return {
                            "id": item_id,
                            "error": err_str,
                            "status": "failed",
                        }
                    await asyncio.sleep(2)

    return {"id": item_id, "error": "Max retries exceeded", "status": "failed"}


async def run_direct_conversion(
    client: genai.Client,
    model_id: str,
    input_path: Path,
    output_dir: Path,
    concurrency: int = 5,
    only_andrej_400: bool = True,
) -> Path:
    """Convert trajectories directly via asynchronous parallel requests with resume checkpointing."""
    output_dir.mkdir(parents=True, exist_ok=True)
    final_dataset_file = output_dir / "manim_narrated_400.jsonl"

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
            print(f"Resuming: found {len(completed_ids)} already converted items in {final_dataset_file.name}")

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

    total_tasks = len(tasks_to_run)
    print(f"Starting direct async conversion for {total_tasks} trajectories (concurrency: {concurrency})...")

    if total_tasks == 0:
        print(f"All items already completed in: {final_dataset_file}")
        return final_dataset_file

    semaphore = asyncio.Semaphore(concurrency)
    write_lock = asyncio.Lock()
    completed_count = len(completed_ids)
    total_expected = completed_count + total_tasks

    async def worker(item_id: str, code: str, current_idx: int) -> None:
        nonlocal completed_count
        result = await _convert_single_item(
            client=client,
            model_id=model_id,
            item_id=item_id,
            code=code,
            semaphore=semaphore,
        )
        async with write_lock:
            with open(final_dataset_file, "a", encoding="utf-8") as out:
                out.write(json.dumps(result) + "\n")
            completed_count += 1
            status_str = result.get("status", "unknown")
            print(f"[{completed_count}/{total_expected}] {item_id}: {status_str}")

    tasks = [
        worker(item_id, code, i + 1)
        for i, (item_id, code) in enumerate(tasks_to_run)
    ]
    await asyncio.gather(*tasks)

    print(f"\nDirect conversion completed! Saved to: {final_dataset_file}")
    return final_dataset_file


def run_conversion(
    api_key: str,
    model_id: str,
    input_path: Path,
    output_dir: Path,
    mode: str = "auto",
    concurrency: int = 5,
    poll_interval: int = 30,
) -> Path:
    """Run narration conversion in batch, direct, or auto-fallback mode."""
    if genai is None:
        raise ImportError(
            "The 'google-genai' package is required. Install with `uv add google-genai`."
        )

    client = genai.Client(api_key=api_key)
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_input_file = output_dir / "manim_batch_input.jsonl"
    batch_output_file = output_dir / "batch_output.jsonl"
    final_dataset_file = output_dir / "manim_narrated_400.jsonl"

    # If user explicitly requested direct mode
    if mode == "direct":
        return asyncio.run(
            run_direct_conversion(
                client=client,
                model_id=model_id,
                input_path=input_path,
                output_dir=output_dir,
                concurrency=concurrency,
            )
        )

    # Otherwise attempt Batch API
    print("Step 1: Preparing batch payload...")
    request_count = prepare_batch_file(input_path, batch_input_file)
    if request_count == 0:
        raise RuntimeError("No valid code trajectories found in input file.")

    print("Step 2: Uploading batch request payload to Google Files API...")
    uploaded_file = client.files.upload(
        file=str(batch_input_file),
        config=types.UploadFileConfig(
            display_name="manim-narration-batch",
            mime_type="application/jsonl",
        ),
    )
    print(f"Uploaded file ID: {uploaded_file.name}")

    print("Step 3: Initiating Gemini 2.5 Flash Batch Job...")
    try:
        batch_job = client.batches.create(
            model=model_id,
            src=uploaded_file.name,
            config={"display_name": "manim-voiceover-conversion-400"},
        )
        print(f"Batch Job Created: {batch_job.name}")
    except errors.APIError as err:
        err_msg = str(err)
        if mode == "auto" and ("FAILED_PRECONDITION" in err_msg or err.code == 400):
            print("\n[Notice] Google AI Studio Batch API requires a Google Cloud project with billing enabled (Tier 1).")
            print("[Notice] Your API key is currently in Free/Standard tier.")
            print("[Notice] Automatically switching to Direct Async Conversion mode (with resume checkpointing)...\n")
            return asyncio.run(
                run_direct_conversion(
                    client=client,
                    model_id=model_id,
                    input_path=input_path,
                    output_dir=output_dir,
                    concurrency=concurrency,
                )
            )
        else:
            raise

    print("Step 4: Polling batch job status...")
    while True:
        job_status = client.batches.get(name=batch_job.name)
        state = getattr(job_status.state, "name", str(job_status.state))
        print(f"Job Status: {state}")

        if state in ["JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED"]:
            break
        time.sleep(poll_interval)

    if state != "JOB_STATE_SUCCEEDED":
        raise RuntimeError(f"Batch job failed with state: {state}")

    print("Step 5: Downloading batch job results...")
    client.files.download(file=job_status.output.name, destination=str(batch_output_file))

    print("Step 6: Processing and compiling final dataset...")
    final_dataset: List[Dict[str, Any]] = []

    with open(batch_output_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                res = json.loads(line)
            except json.JSONDecodeError:
                continue

            custom_id = res.get("key")
            try:
                raw_text = res["response"]["candidates"][0]["content"]["parts"][0]["text"]
                match = re.search(r"```python\s*(.*?)\s*```", raw_text, re.DOTALL)
                clean_code = match.group(1).strip() if match else raw_text.strip()

                final_dataset.append(
                    {
                        "id": custom_id,
                        "narrated_manim_code": clean_code,
                        "status": "success",
                    }
                )
            except (KeyError, IndexError, AttributeError) as parse_err:
                final_dataset.append(
                    {
                        "id": custom_id,
                        "error": str(parse_err),
                        "status": "failed",
                    }
                )

    with open(final_dataset_file, "w", encoding="utf-8") as out:
        for item in final_dataset:
            out.write(json.dumps(item) + "\n")

    print(f"Successfully created narrated dataset ({len(final_dataset)} items): {final_dataset_file}")
    return final_dataset_file


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert Manim trajectory dataset to manim-voiceover scripts using Gemini 2.5 Flash"
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
        "--model-id",
        default=DEFAULT_MODEL_ID,
        help=f"Gemini model ID (default: {DEFAULT_MODEL_ID})",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "batch", "direct"],
        default="auto",
        help="Conversion mode: 'auto' (batch with direct fallback), 'batch', or 'direct' (default: auto)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Number of concurrent API requests in direct mode (default: 5)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Batch polling interval in seconds (default: 30)",
    )
    return parser


def main() -> int:
    init_environment()
    args = build_arg_parser().parse_args()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: Set GEMINI_API_KEY in environment or .env file.", file=sys.stderr)
        return 1

    try:
        run_conversion(
            api_key=api_key,
            model_id=args.model_id,
            input_path=args.input_path.resolve(),
            output_dir=args.output_dir.resolve(),
            mode=args.mode,
            concurrency=args.concurrency,
            poll_interval=args.poll_interval,
        )
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
