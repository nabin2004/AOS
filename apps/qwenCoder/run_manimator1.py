#!/usr/bin/env python3
"""Master End-to-End Pipeline for qwen-Manimator-1 SFT, Merge, GGUF & Dual HF Push.

Trains Qwen/Qwen3-8B on apps/new_data/train.jsonl and produces three HF releases:
  - LoRA Adapter : nabin2004/qwen-Manimator-1-sft
  - Merged Model : nabin2004/qwen-Manimator-1-merged
  - GGUF Q4+Q8   : nabin2004/qwen-Manimator-1-gguf

Usage (Kaggle T4×2):
    python3 run_manimator1.py --kaggle-t4x2 --push-to-hub
    python3 run_manimator1.py --kaggle-t4x2 --push-to-hub --skip-merge --skip-gguf
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

QWEN_ROOT = Path(__file__).resolve().parent
REPO_ROOT = QWEN_ROOT.parent.parent
if str(QWEN_ROOT) not in sys.path:
    sys.path.insert(0, str(QWEN_ROOT))

from identity import (  # noqa: E402
    HUB_MANIMATOR1_GGUF_REPO,
    HUB_MANIMATOR1_MERGED_REPO,
    HUB_MANIMATOR1_SFT_REPO,
    MANIMATOR1_GGUF_OUTPUT_DIR_NAME,
    MANIMATOR1_MERGED_OUTPUT_DIR_NAME,
    MANIMATOR1_SFT_OUTPUT_DIR_NAME,
    OLLAMA_MANIMATOR1_TAG,
    QWEN3_8B_MODEL_ID,
    WANDB_MANIMATOR1_GROUP,
    WANDB_MANIMATOR1_RUN_NAME,
)

# Default local dataset shipped with this repo
# train_clean.jsonl has 305 validated examples (2 malformed rows from train.jsonl removed)
DEFAULT_DATA_PATH = REPO_ROOT / "apps" / "new_data" / "train_clean.jsonl"


def _run_cmd(cmd: list[str], cwd: Path | None = None) -> None:
    print("\n=================================================================")
    print(f"🚀 Executing: {' '.join(str(c) for c in cmd)}")
    print("=================================================================\n")
    subprocess.run([str(c) for c in cmd], cwd=str(cwd) if cwd else None, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="qwen-Manimator-1: E2E SFT, Merge, GGUF & HF Upload Pipeline"
    )
    parser.add_argument(
        "--model-id", default=QWEN3_8B_MODEL_ID, help="Base HF model ID"
    )
    parser.add_argument(
        "--data-path",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help=f"Local JSONL dataset path (default: {DEFAULT_DATA_PATH})",
    )
    parser.add_argument(
        "--adapter-dir",
        type=Path,
        default=QWEN_ROOT / MANIMATOR1_SFT_OUTPUT_DIR_NAME,
    )
    parser.add_argument(
        "--merged-dir",
        type=Path,
        default=QWEN_ROOT / MANIMATOR1_MERGED_OUTPUT_DIR_NAME,
    )
    parser.add_argument(
        "--gguf-dir",
        type=Path,
        default=QWEN_ROOT / MANIMATOR1_GGUF_OUTPUT_DIR_NAME,
    )
    parser.add_argument(
        "--hub-adapter-repo", default=HUB_MANIMATOR1_SFT_REPO, help="HF repo for adapter"
    )
    parser.add_argument(
        "--hub-merged-repo", default=HUB_MANIMATOR1_MERGED_REPO, help="HF repo for merged model"
    )
    parser.add_argument(
        "--hub-gguf-repo", default=HUB_MANIMATOR1_GGUF_REPO, help="HF repo for quantized GGUF"
    )
    parser.add_argument(
        "--quantize-types",
        nargs="+",
        default=["Q4_K_M", "Q8_0"],
        help="GGUF quantization types (default: Q4_K_M Q8_0)",
    )
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--seq-len", type=int, default=4500)
    parser.add_argument("--save-steps", type=int, default=200)
    parser.add_argument("--max-samples", type=int, default=0, help="0 = all samples")
    parser.add_argument(
        "--kaggle-t4x2",
        action="store_true",
        help="Apply Kaggle T4×2 hardware preset (fp16, seq=4500, warmup_ratio=0.05)",
    )
    parser.add_argument("--push-to-hub", action="store_true", help="Push outputs to HF Hub")
    parser.add_argument("--skip-train", action="store_true", help="Skip SFT training phase")
    parser.add_argument("--skip-merge", action="store_true", help="Skip adapter merging phase")
    parser.add_argument("--skip-gguf", action="store_true", help="Skip GGUF export phase")
    args = parser.parse_args()

    adapter_dir = args.adapter_dir.expanduser().resolve()
    merged_dir = args.merged_dir.expanduser().resolve()
    gguf_dir = args.gguf_dir.expanduser().resolve()
    data_path = args.data_path.expanduser().resolve()
    python_exe = sys.executable

    print("=================================================================")
    print("🎨 qwen-Manimator-1 — End-to-End Pipeline")
    print(f"Model:      {args.model_id}")
    print(f"Dataset:    {data_path}")
    print(f"Adapter:    {adapter_dir}")
    print(f"Merged:     {merged_dir}")
    print(f"GGUF:       {gguf_dir}")
    print(f"Hub Repos:  {args.hub_adapter_repo} | {args.hub_merged_repo} | {args.hub_gguf_repo}")
    print("=================================================================")

    # -------------------------------------------------------------------------
    # STEP 1: QLoRA SFT Training
    # -------------------------------------------------------------------------
    if not args.skip_train:
        print("\n▶ STEP 1: Starting QLoRA SFT Training (qwen-Manimator-1)...")
        if not data_path.is_file():
            print(f"ERROR: dataset not found at {data_path}", file=sys.stderr)
            return 1

        train_cmd = [
            python_exe,
            str(QWEN_ROOT / "run.py"),
            "--model-id", args.model_id,
            "--data-path", str(data_path),
            "--output-dir", str(adapter_dir),
            "--epochs", str(args.epochs),
            "--seq-len", str(args.seq_len),
            "--save-steps", str(args.save_steps),
            "--max-samples", str(args.max_samples),
            "--run-name", WANDB_MANIMATOR1_RUN_NAME,
            "--use-4bit",
            "--no-packing",
        ]
        if args.kaggle_t4x2:
            train_cmd.append("--t4x2")
        if args.push_to_hub:
            train_cmd.extend(["--push-to-hub", "--hub-model-id", args.hub_adapter_repo])

        _run_cmd(train_cmd, cwd=QWEN_ROOT)
        print("✔ STEP 1 Complete: LoRA adapter ready.")
    else:
        print("\n⏭ Skipping STEP 1 (SFT Training).")

    # -------------------------------------------------------------------------
    # STEP 2: Merge LoRA Adapter with Base LLM
    # -------------------------------------------------------------------------
    if not args.skip_merge:
        print("\n▶ STEP 2: Merging LoRA Adapter into Base LLM Weights...")
        merge_cmd = [
            python_exe,
            str(QWEN_ROOT / "merge_adapter.py"),
            "--adapter-dir", str(adapter_dir),
            "--output-dir", str(merged_dir),
            "--model-id", args.model_id,
        ]
        if args.push_to_hub:
            merge_cmd.extend(["--push-to-hub", "--hub-repo-id", args.hub_merged_repo])

        _run_cmd(merge_cmd, cwd=QWEN_ROOT)
        print("✔ STEP 2 Complete: Merged model saved and pushed.")
    else:
        print("\n⏭ Skipping STEP 2 (Adapter Merging).")

    # -------------------------------------------------------------------------
    # STEP 3: Multi-Quantization GGUF Export
    # -------------------------------------------------------------------------
    if not args.skip_gguf:
        print("\n▶ STEP 3: Exporting Merged Model to GGUF (Multi-Quant)...")
        gguf_dir.mkdir(parents=True, exist_ok=True)

        for q_type in args.quantize_types:
            print(f"\n---> Quantizing variant: {q_type}")
            gguf_cmd = [
                python_exe,
                str(QWEN_ROOT / "export_gguf.py"),
                "--model-dir", str(merged_dir),
                "--output-dir", str(gguf_dir),
                "--quantize", q_type,
                "--model-name", OLLAMA_MANIMATOR1_TAG,
                "--skip-ollama-create",  # no Ollama on Kaggle
            ]
            _run_cmd(gguf_cmd, cwd=QWEN_ROOT)

        if args.push_to_hub:
            from hub_upload import push_model_folder, require_token  # noqa: PLC0415

            print(f"\n---> Pushing GGUF repo ({args.hub_gguf_repo}) to HF Hub...")
            token = require_token()
            push_model_folder(
                gguf_dir,
                args.hub_gguf_repo,
                token,
                private=False,
                ignore_patterns=["*-f16.gguf"],
            )
            print("✔ GGUF repository pushed to Hugging Face!")

        print("✔ STEP 3 Complete: Multi-quant GGUF models ready.")
    else:
        print("\n⏭ Skipping STEP 3 (GGUF Export).")

    print("\n=================================================================")
    print("🎉 qwen-Manimator-1 End-to-End Pipeline Complete!")
    print(f"  Adapter : https://huggingface.co/{args.hub_adapter_repo}")
    print(f"  Merged  : https://huggingface.co/{args.hub_merged_repo}")
    print(f"  GGUF    : https://huggingface.co/{args.hub_gguf_repo}")
    print("=================================================================\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
