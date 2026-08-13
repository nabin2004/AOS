#!/usr/bin/env python3
"""Build DPO preference pairs from Code Agent trajectories.

Chosen = shortest successful run with has_audio=True (when available).
Rejected = a failed / no-audio / longer bad run on the same prompt, or a
synthesized CodeMode-violating first turn when no natural reject exists.

Usage (from apps/agents):

    uv run python build_preference_pairs.py
    uv run python build_preference_pairs.py --scan-workspace --train-split 0.9
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

AGENTS_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(AGENTS_ROOT))

from export_local_sft import (  # noqa: E402
    convert_trajectory_record,
    load_trajectory_jsonl,
    scan_workspace_trajectories,
)
from export_traces.trajectory_select import prompt_hash, trajectory_score  # noqa: E402
from export_traces.validate import split_train_val, write_jsonl  # noqa: E402

DEFAULT_INPUT = AGENTS_ROOT / "training_data" / "trajectories.jsonl"
DEFAULT_OUTPUT = AGENTS_ROOT / "export_traces" / "coder_sft" / "preference"


def _is_gold(record: dict[str, Any]) -> bool:
    if not record.get("success"):
        return False
    if not record.get("final_code"):
        return False
    # Prefer explicit audio; treat missing has_audio as acceptable legacy gold.
    if record.get("has_audio") is False:
        return False
    return True


def _reject_reason(record: dict[str, Any]) -> str:
    if not record.get("success"):
        return "compile_fail"
    if record.get("has_audio") is False:
        return "no_audio"
    return "longer_or_weaker"


def _synthesize_rejected_messages(chosen_messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build a rejected tool-trace that violates CodeMode (raw manim import)."""
    user = next((m for m in chosen_messages if m.get("role") == "user"), None)
    prompt = (user or {}).get("content") or "Create a Manim animation."
    bad_code = "from manim import *\n\nclass BadScene(Scene):\n    def construct(self):\n        self.wait(1)\n"
    return [
        {"role": "user", "content": prompt},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_reject_0",
                    "type": "function",
                    "function": {
                        "name": "run_code",
                        "arguments": {"code": bad_code},
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_reject_0",
            "name": "run_code",
            "content": json.dumps(
                {"ok": False, "error": "codemode_star_import"},
                ensure_ascii=False,
            ),
        },
    ]


def _to_tool_trace(record: dict[str, Any]) -> dict[str, Any] | None:
    _, tt_row, _ = convert_trajectory_record(
        record,
        sft_format="tool_trace",
        keep_thinking=False,
        max_tool_result_chars=8192,
    )
    return tt_row


def build_preference_pairs(
    records: list[dict[str, Any]],
    *,
    synthesize_missing_rejects: bool = True,
) -> list[dict[str, Any]]:
    by_prompt: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        key = prompt_hash(record)
        if key is None:
            continue
        by_prompt[key].append(record)

    pairs: list[dict[str, Any]] = []
    for group in by_prompt.values():
        gold = [r for r in group if _is_gold(r)]
        if not gold:
            continue
        chosen_rec = max(gold, key=trajectory_score)
        chosen_tt = _to_tool_trace(chosen_rec)
        if not chosen_tt or not chosen_tt.get("messages"):
            continue

        rejects = [r for r in group if r is not chosen_rec and not _is_gold(r)]
        if not rejects:
            rejects = [r for r in group if r is not chosen_rec]

        rejected_messages: list[dict[str, Any]] | None = None
        rejected_reason = "synthesized_codemode_violation"
        rejected_run = None

        if rejects:
            rejected_rec = min(rejects, key=trajectory_score)
            rejected_tt = _to_tool_trace(rejected_rec)
            if rejected_tt and rejected_tt.get("messages"):
                rejected_messages = rejected_tt["messages"]
                rejected_reason = _reject_reason(rejected_rec)
                rejected_run = rejected_rec.get("run_dir")

        if rejected_messages is None:
            if not synthesize_missing_rejects:
                continue
            rejected_messages = _synthesize_rejected_messages(chosen_tt["messages"])

        pairs.append(
            {
                "prompt": chosen_rec.get("user_prompt", ""),
                "chosen": {"messages": chosen_tt["messages"]},
                "rejected": {"messages": rejected_messages},
                "metadata": {
                    "chosen_run_dir": chosen_rec.get("run_dir"),
                    "rejected_run_dir": rejected_run,
                    "rejected_reason": rejected_reason,
                    "chosen_has_audio": chosen_rec.get("has_audio"),
                    "chosen_success": chosen_rec.get("success"),
                },
            }
        )

    return pairs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--scan-workspace", action="store_true")
    parser.add_argument("--train-split", type=float, default=0.9)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--no-synthesize",
        action="store_true",
        help="Skip pairs that lack a natural rejected trajectory",
    )
    args = parser.parse_args()

    if args.scan_workspace:
        records = scan_workspace_trajectories()
        source = "workspace"
    else:
        if not args.input.is_file():
            print(f"ERROR: missing {args.input}", file=sys.stderr)
            return 1
        records = load_trajectory_jsonl(args.input)
        source = str(args.input)

    pairs = build_preference_pairs(
        records,
        synthesize_missing_rejects=not args.no_synthesize,
    )
    print(f"Built {len(pairs)} preference pairs from {len(records)} records ({source})")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.train_split and 0.0 < args.train_split < 1.0 and pairs:
        train_rows, val_rows = split_train_val(
            pairs, args.train_split, seed=args.seed
        )
        write_jsonl(args.output_dir / "train.jsonl", train_rows)
        write_jsonl(args.output_dir / "val.jsonl", val_rows)
        print(f"Wrote {args.output_dir / 'train.jsonl'} ({len(train_rows)})")
        print(f"Wrote {args.output_dir / 'val.jsonl'} ({len(val_rows)})")
    else:
        write_jsonl(args.output_dir / "train.jsonl", pairs)
        print(f"Wrote {args.output_dir / 'train.jsonl'} ({len(pairs)})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
