#!/usr/bin/env python3
"""Master End-to-End Pipeline for Qwen3-8B SFT, Merging, Multi-Quantization & Dual HF Push.

Lifecycle Steps:
1. QLoRA SFT training on Qwen3-8B (5k Manim + 400 AOS Trajectories dataset).
2. Pushing LoRA adapter to Hugging Face Hub (nabin2004/AOS-qwen3-8b-adapter).
3. Merging LoRA adapter with Qwen3-8B base LLM.
4. Pushing merged full-weight model to Hugging Face Hub (nabin2004/AOS-Qwen3-8B-Merged).
5. Converting merged weights to GGUF & multi-quantization (Q4_K_M and Q8_0).
6. Pushing quantized GGUF artifacts & Ollama Modelfile to dedicated HF repo (nabin2004/AOS-Qwen3-8B-GGUF).

Usage:
    uv run python run_e2e_qwen3.py
    uv run python run_e2e_qwen3.py --kaggle --push-to-hub
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

QWEN_ROOT = Path(__file__).resolve().parent
if str(QWEN_ROOT) not in sys.path:
    sys.path.insert(0, str(QWEN_ROOT))

from hub_upload import push_model_folder, require_token
from identity import (
    HUB_QWEN3_8B_DATASET_REPO,
    HUB_QWEN3_8B_GGUF_REPO,
    HUB_QWEN3_8B_MERGED_REPO,
    HUB_QWEN3_8B_SFT_REPO,
    OLLAMA_QWEN3_8B_TAG,
    QWEN3_8B_GGUF_OUTPUT_DIR_NAME,
    QWEN3_8B_MERGED_OUTPUT_DIR_NAME,
    QWEN3_8B_MODEL_ID,
    QWEN3_8B_SFT_OUTPUT_DIR_NAME,
)


def _run_cmd(cmd: list[str], cwd: Path | None = None) -> None:
    print(f"\n=================================================================")
    print(f"🚀 Executing Command: {' '.join(cmd)}")
    print(f"=================================================================\n")
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="End-to-End Qwen3-8B SFT, Merge, GGUF & HF Upload Pipeline")
    parser.add_argument("--model-id", default=QWEN3_8B_MODEL_ID, help="Base Hugging Face model ID")
    parser.add_argument("--dataset-repo", default=HUB_QWEN3_8B_DATASET_REPO, help="Dataset repo ID")
    parser.add_argument("--adapter-dir", type=Path, default=QWEN_ROOT / QWEN3_8B_SFT_OUTPUT_DIR_NAME)
    parser.add_argument("--merged-dir", type=Path, default=QWEN_ROOT / QWEN3_8B_MERGED_OUTPUT_DIR_NAME)
    parser.add_argument("--gguf-dir", type=Path, default=QWEN_ROOT / QWEN3_8B_GGUF_OUTPUT_DIR_NAME)

    parser.add_argument("--hub-adapter-repo", default=HUB_QWEN3_8B_SFT_REPO, help="HF repo for adapter")
    parser.add_argument("--hub-merged-repo", default=HUB_QWEN3_8B_MERGED_REPO, help="HF repo for merged model")
    parser.add_argument("--hub-gguf-repo", default=HUB_QWEN3_8B_GGUF_REPO, help="HF repo for quantized GGUF")
    parser.add_argument("--quantize-types", nargs="+", default=["Q4_K_M", "Q8_0"], help="GGUF quant types")

    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--seq-len", type=int, default=2048)
    parser.add_argument("--save-steps", type=int, default=200)
    parser.add_argument("--max-samples", type=int, default=0, help="0 = all samples")
    parser.add_argument("--kaggle", action="store_true", help="Apply Kaggle P100 hardware preset")
    parser.add_argument("--push-to-hub", action="store_true", help="Push outputs to Hugging Face Hub")

    parser.add_argument("--skip-train", action="store_true", help="Skip SFT training phase")
    parser.add_argument("--skip-merge", action="store_true", help="Skip adapter merging phase")
    parser.add_argument("--skip-gguf", action="store_true", help="Skip GGUF quantization phase")
    args = parser.parse_args()

    adapter_dir = args.adapter_dir.expanduser().resolve()
    merged_dir = args.merged_dir.expanduser().resolve()
    gguf_dir = args.gguf_dir.expanduser().resolve()

    python_exe = sys.executable

    # -------------------------------------------------------------------------
    # STEP 1: QLoRA SFT Training
    # -------------------------------------------------------------------------
    if not args.skip_train:
        print("\n▶ STEP 1: Starting QLoRA SFT Training...")
        train_cmd = [
            python_exe,
            str(QWEN_ROOT / "run.py"),
            "--model-id", args.model_id,
            "--dataset-repo", args.dataset_repo,
            "--output-dir", str(adapter_dir),
            "--epochs", str(args.epochs),
            "--seq-len", str(args.seq_len),
            "--save-steps", str(args.save_steps),
            "--max-samples", str(args.max_samples),
            "--use-4bit",
            "--no-packing",
        ]
        if args.kaggle:
            train_cmd.append("--kaggle")
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
        print("\n▶ STEP 2: Merging LoRA Adapter into Full Base LLM Weights...")
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
    # STEP 3: Multi-Quantization GGUF Export (Q4_K_M and Q8_0)
    # -------------------------------------------------------------------------
    if not args.skip_gguf:
        print("\n▶ STEP 3: Quantizing Merged Model to GGUF (Multi-Quant)...")
        gguf_dir.mkdir(parents=True, exist_ok=True)

        for q_type in args.quantize_types:
            print(f"\n---> Quantizing variant: {q_type}")
            gguf_cmd = [
                python_exe,
                str(QWEN_ROOT / "export_gguf.py"),
                "--model-dir", str(merged_dir),
                "--output-dir", str(gguf_dir),
                "--quantize", q_type,
                "--model-name", OLLAMA_QWEN3_8B_TAG,
            ]
            _run_cmd(gguf_cmd, cwd=QWEN_ROOT)

        if args.push_to_hub:
            print(f"\n---> Pushing GGUF repository to Hugging Face ({args.hub_gguf_repo})...")
            token = require_token()
            push_model_folder(
                gguf_dir,
                args.hub_gguf_repo,
                token,
                private=False,
            )
            print("✔ GGUF repository successfully pushed to Hugging Face!")

        print("✔ STEP 3 Complete: Multi-quantization GGUF models ready.")
    else:
        print("\n⏭ Skipping STEP 3 (GGUF Quantization).")

    print("\n=================================================================")
    print("🎉 Qwen3-8B End-to-End Pipeline Execution Completed Successfully!")
    print("=================================================================\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
