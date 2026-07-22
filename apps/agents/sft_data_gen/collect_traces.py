#!/usr/bin/env python3
"""Batch-run agent_graph over prompts.jsonl to produce Code Agent SFT traces.

Each run writes structured artifacts under workspace/coder_runs/ and appends to
training_data/trajectories.jsonl for export_local_sft.py.

Usage (from apps/agents):

    uv run python sft_data_gen/collect_traces.py --limit 10 --resume
    uv run python sft_data_gen/collect_traces.py --limit 100 --fast --convert-after-local
    uv run python sft_data_gen/collect_traces.py --dry-run --limit 3
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

AGENTS_ROOT = Path(__file__).resolve().parent.parent
SFT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(AGENTS_ROOT))

load_dotenv(AGENTS_ROOT / ".env")
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_PROMPTS = SFT_DIR / "prompts.jsonl"
DEFAULT_MANIFEST = SFT_DIR / "batch_runs.jsonl"
DEFAULT_SUMMARY = SFT_DIR / "batch_summary.json"
EXPORT_SCRIPT = AGENTS_ROOT / "export_coder_sft.py"
LOCAL_EXPORT_SCRIPT = AGENTS_ROOT / "export_local_sft.py"


def apply_batch_env(*, fast: bool) -> None:
    """Configure env for batch SFT collection before agent modules import."""
    if fast:
        os.environ["AOS_LOGFIRE"] = "0"
        os.environ["AOS_DBOS"] = "0"
        os.environ["AOS_SFT_BATCH"] = "1"
    else:
        os.environ.setdefault("AOS_LOGFIRE", "0")
        os.environ.setdefault("AOS_DBOS", "0")


def warmup_models() -> None:
    """Preload Manim doc RAG index once (avoids ~10s cold start per first search)."""
    from tools.manim_docs import _get_index

    logger.info("Warming up Manim doc RAG index...")
    _get_index()
    logger.info("Manim doc RAG index ready.")


def load_prompts(path: Path) -> list[dict[str, Any]]:
    """Load prompt records from JSONL. Each line must have a 'prompt' string."""
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping invalid JSON at line %s: %s", line_no, exc)
                continue
            prompt = row.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                logger.warning("Skipping line %s: missing 'prompt' string", line_no)
                continue
            index = row.get("index")
            if index is None:
                index = line_no - 1
            records.append(
                {
                    "index": int(index),
                    "prompt": prompt.strip(),
                    "topic": row.get("topic"),
                }
            )
    return records


def parse_indices(raw: str | None) -> set[int] | None:
    if not raw:
        return None
    return {int(part.strip()) for part in raw.split(",") if part.strip()}


def load_completed_indices(manifest_path: Path, *, skip_failed: bool) -> set[int]:
    """Return indices to skip when resuming."""
    if not manifest_path.is_file():
        return set()
    completed: set[int] = set()
    with manifest_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            index = row.get("index")
            status = row.get("status")
            if index is None:
                continue
            if status == "ok":
                completed.add(int(index))
            elif skip_failed and status in ("failed", "skipped"):
                completed.add(int(index))
    return completed


def select_prompts(
    records: list[dict[str, Any]],
    *,
    offset: int,
    limit: int | None,
    indices: set[int] | None,
    resume: bool,
    skip_failed: bool,
    manifest_path: Path,
) -> list[dict[str, Any]]:
    selected = records
    if indices is not None:
        selected = [r for r in selected if r["index"] in indices]
    if offset:
        selected = selected[offset:]
    if limit is not None:
        selected = selected[:limit]

    if resume:
        done = load_completed_indices(manifest_path, skip_failed=skip_failed)
        before = len(selected)
        selected = [r for r in selected if r["index"] not in done]
        skipped = before - len(selected)
        if skipped:
            logger.info("Resume: skipping %s already completed prompt(s)", skipped)
    return selected


async def append_manifest(
    manifest_path: Path,
    record: dict[str, Any],
    *,
    lock: asyncio.Lock,
) -> None:
    line = json.dumps(record, ensure_ascii=False) + "\n"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    async with lock:
        with manifest_path.open("a", encoding="utf-8") as f:
            f.write(line)


def write_summary(summary_path: Path, stats: dict[str, Any]) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def run_export(days: int) -> int:
    cmd = [sys.executable, str(EXPORT_SCRIPT), "--days", str(days)]
    logger.info("Running export: %s", " ".join(cmd))
    return subprocess.call(cmd, cwd=AGENTS_ROOT)


def run_local_export() -> int:
    cmd = [sys.executable, str(LOCAL_EXPORT_SCRIPT)]
    logger.info("Running local export: %s", " ".join(cmd))
    return subprocess.call(cmd, cwd=AGENTS_ROOT)


async def _run_one_impl(record: dict[str, Any]) -> dict[str, Any]:
    from agent_graph import run_pipeline

    index = record["index"]
    prompt = record["prompt"]
    timestamp = datetime.now(UTC).isoformat()

    logger.info("Running index=%s prompt=%.80s...", index, prompt)
    try:
        result = await run_pipeline(prompt, prompt_index=index)
        manifest_row = {
            "index": index,
            "prompt": prompt,
            "status": "ok",
            "compile_ok": bool(result.get("compile_ok")),
            "run_dir": result.get("run_dir"),
            "traces_path": result.get("traces_path"),
            "stopped_reason": result.get("stopped_reason"),
            "timestamp": timestamp,
        }
        logger.info(
            "Done index=%s compile_ok=%s run_dir=%s",
            index,
            manifest_row["compile_ok"],
            manifest_row["run_dir"],
        )
        return manifest_row
    except Exception as exc:
        logger.exception("Failed index=%s: %s", index, exc)
        return {
            "index": index,
            "prompt": prompt,
            "status": "failed",
            "error": str(exc),
            "timestamp": timestamp,
        }


async def _run_bounded(
    record: dict[str, Any],
    *,
    sem: asyncio.Semaphore,
    manifest_path: Path,
    write_lock: asyncio.Lock,
) -> dict[str, Any]:
    async with sem:
        row = await _run_one_impl(record)
        await append_manifest(manifest_path, row, lock=write_lock)
        return row


def _record_stats(stats: dict[str, Any], row: dict[str, Any]) -> None:
    stats["attempted"] += 1
    if row.get("status") == "ok":
        stats["ok"] += 1
        if row.get("compile_ok"):
            stats["compile_ok"] += 1
            stats["compile_ok_indices"].append(row["index"])
    else:
        stats["failed"] += 1
        stats["failed_indices"].append(row["index"])


async def collect_traces(args: argparse.Namespace) -> dict[str, Any]:
    prompts_path = args.prompts.resolve()
    manifest_path = args.manifest.resolve()

    if not prompts_path.is_file():
        raise FileNotFoundError(f"Prompts file not found: {prompts_path}")

    all_records = load_prompts(prompts_path)
    indices = parse_indices(args.indices)
    to_run = select_prompts(
        all_records,
        offset=args.offset,
        limit=args.limit,
        indices=indices,
        resume=args.resume,
        skip_failed=args.skip_failed,
        manifest_path=manifest_path,
    )

    logger.info(
        "Loaded %s prompts; %s selected for this run (concurrency=%s)",
        len(all_records),
        len(to_run),
        args.concurrency,
    )

    if args.dry_run:
        for rec in to_run:
            print(f"[dry-run] index={rec['index']} prompt={rec['prompt'][:120]}...")
        return {
            "dry_run": True,
            "selected": len(to_run),
            "indices": [r["index"] for r in to_run],
        }

    if args.warmup:
        warmup_models()

    sem = asyncio.Semaphore(args.concurrency)
    write_lock = asyncio.Lock()
    stats: dict[str, Any] = {
        "started_at": datetime.now(UTC).isoformat(),
        "prompts_file": str(prompts_path),
        "manifest_file": str(manifest_path),
        "concurrency": args.concurrency,
        "fast": args.fast,
        "attempted": 0,
        "ok": 0,
        "failed": 0,
        "compile_ok": 0,
        "failed_indices": [],
        "compile_ok_indices": [],
    }

    if args.fail_fast:
        for rec in to_run:
            row = await _run_bounded(
                rec,
                sem=sem,
                manifest_path=manifest_path,
                write_lock=write_lock,
            )
            _record_stats(stats, row)
            if row.get("status") != "ok":
                logger.error("Fail-fast: stopping after index=%s", row["index"])
                break
    else:
        tasks = [
            asyncio.create_task(
                _run_bounded(
                    rec,
                    sem=sem,
                    manifest_path=manifest_path,
                    write_lock=write_lock,
                )
            )
            for rec in to_run
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for rec, result in zip(to_run, results, strict=True):
            if isinstance(result, BaseException):
                row = {
                    "index": rec["index"],
                    "prompt": rec["prompt"],
                    "status": "failed",
                    "error": str(result),
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                await append_manifest(manifest_path, row, lock=write_lock)
                _record_stats(stats, row)
            else:
                _record_stats(stats, result)

    stats["finished_at"] = datetime.now(UTC).isoformat()
    write_summary(args.summary.resolve(), stats)
    logger.info(
        "Batch complete: attempted=%s ok=%s compile_ok=%s failed=%s",
        stats["attempted"],
        stats["ok"],
        stats["compile_ok"],
        stats["failed"],
    )
    return stats


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run agent_graph over prompts.jsonl to collect Code Agent SFT traces",
    )
    parser.add_argument(
        "--prompts",
        type=Path,
        default=DEFAULT_PROMPTS,
        help=f"Input JSONL with {{index, prompt}} (default: {DEFAULT_PROMPTS.name})",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help=f"Append-only progress log (default: {DEFAULT_MANIFEST.name})",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=DEFAULT_SUMMARY,
        help=f"Batch summary JSON (default: {DEFAULT_SUMMARY.name})",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max prompts this run")
    parser.add_argument(
        "--offset", type=int, default=0, help="Skip first N prompts after filtering"
    )
    parser.add_argument(
        "--indices",
        type=str,
        default=None,
        help="Comma-separated prompt indices to run (e.g. 0,3,7)",
    )
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip indices already marked ok in manifest (default: on)",
    )
    parser.add_argument(
        "--skip-failed",
        action="store_true",
        help="With --resume, also skip indices that previously failed",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=2,
        help="Parallel pipeline runs (default: 2)",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Disable Logfire/DBOS, skip narration, warm up RAG index (recommended for batch SFT)",
    )
    parser.add_argument(
        "--no-warmup",
        action="store_true",
        help="Skip Manim doc RAG preload (warmup runs by default with --fast)",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first failed run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print selected prompts without calling agents",
    )
    parser.add_argument(
        "--export-after",
        action="store_true",
        help="Run export_coder_sft.py when batch finishes (Logfire)",
    )
    parser.add_argument(
        "--convert-after-local",
        action="store_true",
        help="Run export_local_sft.py when batch finishes (no Logfire token)",
    )
    parser.add_argument(
        "--export-days",
        type=int,
        default=30,
        help="Logfire lookback days for --export-after (default: 30)",
    )
    args = parser.parse_args(argv)
    args.warmup = args.fast and not args.no_warmup
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    apply_batch_env(fast=args.fast)
    if args.fast:
        logger.info(
            "Fast batch mode: Logfire off, DBOS off, skip narration, concurrency=%s",
            args.concurrency,
        )
    try:
        stats = asyncio.run(collect_traces(args))
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        return 130
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 1

    if args.dry_run:
        return 0

    if args.export_after:
        return run_export(args.export_days)

    if args.convert_after_local:
        return run_local_export()

    if stats.get("failed", 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
