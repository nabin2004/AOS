#!/usr/bin/env python3
"""Progress report for SFT synthetic data collection.

Usage (from apps/agents):

    uv run python sft_data_gen/status.py
    uv run python sft_data_gen/status.py --target 5000
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SFT_DIR = Path(__file__).resolve().parent
AGENTS_ROOT = SFT_DIR.parent
DEFAULT_PROMPTS = SFT_DIR / "prompts.jsonl"
DEFAULT_MANIFEST = SFT_DIR / "batch_runs.jsonl"
DEFAULT_SUMMARY = SFT_DIR / "batch_summary.json"
DEFAULT_TRAJECTORIES = AGENTS_ROOT / "training_data" / "trajectories.jsonl"
DEFAULT_TARGET = 5000


def _count_jsonl(path: Path) -> int:
    if not path.is_file():
        return 0
    n = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def _load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _manifest_stats(rows: list[dict]) -> dict:
    """Latest status per prompt index wins (append-only manifest)."""
    by_index: dict[int, dict] = {}
    for row in rows:
        idx = row.get("index")
        if idx is None:
            continue
        by_index[int(idx)] = row

        statuses = Counter()
    compile_ok = 0
    for row in by_index.values():
        status = str(row.get("status") or "unknown")
        if status == "ok":
            statuses["ok"] += 1
        elif status == "failed":
            statuses["failed"] += 1
        else:
            statuses[status] += 1
        if row.get("compile_ok"):
            compile_ok += 1

    return {
        "unique_indices": len(by_index),
        "ok": statuses.get("ok", 0),
        "failed": statuses.get("failed", 0),
        "compile_ok": compile_ok,
        "other": sum(v for k, v in statuses.items() if k not in ("ok", "failed")),
    }


def _trajectory_stats(rows: list[dict]) -> dict:
    success_prompts: set[str] = set()
    success_count = 0
    for row in rows:
        if row.get("success") is False:
            continue
        code = row.get("final_code") or ""
        if not str(code).strip():
            continue
        success_count += 1
        prompt = (row.get("user_prompt") or row.get("prompt") or "").strip()
        if prompt:
            success_prompts.add(prompt)
    return {
        "rows": len(rows),
        "success_rows": success_count,
        "unique_success_prompts": len(success_prompts),
    }


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _eta_hours(
    remaining: int,
    summary: dict | None,
    concurrency: int,
) -> float | None:
    """Estimate hours left from last batch wall time and compile_ok count."""
    if remaining <= 0 or not summary:
        return 0.0 if remaining <= 0 else None
    started = _parse_iso(summary.get("started_at"))
    finished = _parse_iso(summary.get("finished_at"))
    compile_ok = int(summary.get("compile_ok") or 0)
    attempted = int(summary.get("attempted") or 0)
    if not started or not finished or compile_ok <= 0 or attempted <= 0:
        return None
    elapsed_h = (finished - started).total_seconds() / 3600.0
    if elapsed_h <= 0:
        return None
    # Scale by concurrency if last batch used a different setting (best-effort).
    rate = compile_ok / elapsed_h  # compile_ok per hour at that concurrency
    batch_conc = int(summary.get("concurrency") or concurrency or 1)
    if batch_conc > 0 and concurrency > 0 and concurrency != batch_conc:
        rate *= concurrency / batch_conc
    if rate <= 0:
        return None
    return remaining / rate


def report(
    prompts_path: Path,
    manifest_path: Path,
    summary_path: Path,
    trajectories_path: Path,
    target: int,
    concurrency: int,
) -> str:
    prompts_n = _count_jsonl(prompts_path)
    manifest_rows = _load_jsonl(manifest_path)
    mstats = _manifest_stats(manifest_rows)
    traj_rows = _load_jsonl(trajectories_path)
    tstats = _trajectory_stats(traj_rows)

    summary = None
    if summary_path.is_file():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            summary = None

    unique_success = tstats["unique_success_prompts"]
    remaining = max(0, target - unique_success)
    eta = _eta_hours(remaining, summary, concurrency)

    lines = [
        "SFT data collection status",
        "=" * 40,
        f"Prompts bank:              {prompts_n:>6}  ({prompts_path.name})",
        f"Manifest unique indices:   {mstats['unique_indices']:>6}",
        f"  ok:                      {mstats['ok']:>6}",
        f"  failed:                  {mstats['failed']:>6}",
        f"  compile_ok:              {mstats['compile_ok']:>6}",
        f"Trajectories file rows:    {tstats['rows']:>6}",
        f"  success rows:            {tstats['success_rows']:>6}",
        f"  unique success prompts:  {unique_success:>6}",
        f"Target (unique compile_ok):{target:>6}",
        f"Remaining to target:       {remaining:>6}",
    ]

    if summary:
        lines.append("")
        lines.append("Last batch_summary.json")
        lines.append(
            f"  attempted={summary.get('attempted')} ok={summary.get('ok')} "
            f"compile_ok={summary.get('compile_ok')} failed={summary.get('failed')}"
        )
        lines.append(f"  {summary.get('started_at')} → {summary.get('finished_at')}")

    if eta is not None:
        lines.append("")
        if remaining == 0:
            lines.append("ETA: target reached.")
        else:
            lines.append(
                f"ETA (from last batch rate, concurrency={concurrency}): "
                f"~{eta:.1f} hours ({eta / 24:.1f} days)"
            )
    else:
        lines.append("")
        lines.append("ETA: need a finished batch_summary.json with compile_ok > 0.")

    lines.append("")
    lines.append(f"Generated at {datetime.now(timezone.utc).isoformat()}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SFT synthetic data collection status")
    p.add_argument("--prompts", type=Path, default=DEFAULT_PROMPTS)
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    p.add_argument("--trajectories", type=Path, default=DEFAULT_TRAJECTORIES)
    p.add_argument(
        "--target",
        type=int,
        default=DEFAULT_TARGET,
        help=f"Unique compile_ok prompt target (default: {DEFAULT_TARGET})",
    )
    p.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Assumed collector concurrency for ETA scaling (default: 4)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    print(
        report(
            prompts_path=args.prompts,
            manifest_path=args.manifest,
            summary_path=args.summary,
            trajectories_path=args.trajectories,
            target=args.target,
            concurrency=args.concurrency,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
