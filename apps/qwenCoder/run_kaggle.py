#!/usr/bin/env python3
"""Super Simple One-Click Kaggle Runner for Qwen3-8B Pipeline.

Features:
1. Auto-retrieves HF_TOKEN and WANDB_API_KEY from Kaggle UserSecretsClient.
2. Checks PyTorch CUDA compatibility before reinstalling (saves 2.5GB download / ~3 mins).
3. Auto-curates 5,400-sample dataset (nabin2004/manim-aos-5k400) if missing or requested.
4. Executes QLoRA SFT, adapter merging, GGUF multi-quantization (Q4_K_M & Q8_0), and HuggingFace uploads.

Usage in Kaggle Notebook:
    !python3 apps/qwenCoder/run_kaggle.py
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

QWEN_ROOT = Path(__file__).resolve().parent
REPO_ROOT = QWEN_ROOT.parent.parent


def setup_kaggle_secrets() -> None:
    """Retrieve HF_TOKEN and WANDB_API_KEY from Kaggle UserSecretsClient if not set."""
    if "HF_TOKEN" not in os.environ:
        try:
            from kaggle_secrets import UserSecretsClient  # type: ignore

            secrets = UserSecretsClient()
            token = secrets.get_secret("HF_TOKEN")
            if token:
                os.environ["HF_TOKEN"] = token
                print("✔ Successfully retrieved HF_TOKEN from Kaggle UserSecrets.")
        except Exception as exc:
            print(f"Notice: Could not auto-fetch HF_TOKEN from Kaggle secrets: {exc}")

    if "WANDB_API_KEY" not in os.environ:
        try:
            from kaggle_secrets import UserSecretsClient  # type: ignore

            secrets = UserSecretsClient()
            wandb_key = secrets.get_secret("WANDB_API_KEY")
            if wandb_key:
                os.environ["WANDB_API_KEY"] = wandb_key
                print("✔ Successfully retrieved WANDB_API_KEY from Kaggle UserSecrets.")
        except Exception:
            pass


def is_cuda_working() -> bool:
    """Test whether system PyTorch can perform CUDA matrix multiplication."""
    try:
        import torch

        if not torch.cuda.is_available():
            return False
        x = torch.randn(64, 64, device="cuda")
        _ = x @ x
        torch.cuda.synchronize()
        return True
    except Exception:
        return False


def setup_environment(force_reinstall_torch: bool = False) -> None:
    """Install dependencies into Kaggle system Python without unnecessary torch downloads."""
    python_exe = sys.executable

    if not force_reinstall_torch and is_cuda_working():
        import torch
        print(f"✔ PyTorch {torch.__version__} with CUDA ({torch.version.cuda}) is working. Skipping PyTorch re-installation!")
    else:
        print("==> Pinning system torch 2.7.1+cu118 for Kaggle P100 sm_60...")
        subprocess.run(
            [python_exe, "-m", "pip", "uninstall", "-y", "torch", "torchvision", "torchaudio"],
            check=False,
        )
        subprocess.run(
            [
                python_exe,
                "-m",
                "pip",
                "install",
                "torch==2.7.1",
                "torchvision==0.22.1",
                "torchaudio==2.7.1",
                "--index-url",
                "https://download.pytorch.org/whl/cu118",
            ],
            check=True,
        )

    print("==> Installing SFT & quantization dependencies...")
    deps = [
        "accelerate>=1.0.0",
        "bitsandbytes>=0.45.0",
        "datasets>=5.0.0",
        "huggingface-hub>=0.27.0",
        "peft>=0.19.1",
        "transformers>=4.51.0",
        "trl>=0.19.0",
        "wandb>=0.19.0",
        "wrapt",
    ]
    subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([python_exe, "-m", "pip", "install"] + deps, check=True)

    print("==> Installing qwenCoder package in editable mode (--no-deps)...")
    subprocess.run([python_exe, "-m", "pip", "install", "-e", str(QWEN_ROOT), "--no-deps"], check=True)


def ensure_dataset(curate_if_missing: bool = True, push_dataset: bool = True) -> None:
    """Ensure dataset (train.jsonl) is present or curate it automatically."""
    dataset_file = QWEN_ROOT / "curated_sft_5k_400" / "train.jsonl"
    if not dataset_file.exists() and curate_if_missing:
        print("\n==> Dataset file not found locally. Running automatic curation (5,400 samples)...")
        cmd = [sys.executable, str(QWEN_ROOT / "curate_sft_5k_400.py")]
        if push_dataset and os.environ.get("HF_TOKEN"):
            cmd.extend(["--push", "--repo-id", "nabin2004/manim-aos-5k400"])
        subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Super Simple Kaggle One-Click Qwen3-8B Pipeline")
    parser.add_argument("--epochs", type=int, default=1, help="Number of training epochs")
    parser.add_argument("--save-steps", type=int, default=200, help="Checkpoint save steps")
    parser.add_argument("--seq-len", type=int, default=2048, help="Sequence length")
    parser.add_argument("--curate", action="store_true", help="Force dataset curation before training")
    parser.add_argument("--force-reinstall-torch", action="store_true", help="Force reinstall PyTorch cu118")
    parser.add_argument("--skip-train", action="store_true", help="Skip training step")
    parser.add_argument("--skip-merge", action="store_true", help="Skip merge step")
    parser.add_argument("--skip-gguf", action="store_true", help="Skip GGUF quantization step")
    args = parser.parse_args()

    print("=================================================================")
    print("🚀 Starting Simple Kaggle Qwen3-8B Pipeline")
    print("=================================================================")

    setup_kaggle_secrets()

    if not os.environ.get("HF_TOKEN"):
        print("WARNING: HF_TOKEN is not set. Hugging Face uploads will fail unless HF_TOKEN is exported or in Kaggle Secrets.")

    setup_environment(force_reinstall_torch=args.force_reinstall_torch)

    if args.curate:
        print("\n==> Force curating dataset...")
        cmd = [sys.executable, str(QWEN_ROOT / "curate_sft_5k_400.py")]
        if os.environ.get("HF_TOKEN"):
            cmd.extend(["--push", "--repo-id", "nabin2004/manim-aos-5k400"])
        subprocess.run(cmd, check=True)
    else:
        ensure_dataset(curate_if_missing=True, push_dataset=True)

    print("\n==> Launching Master Qwen3-8B End-to-End Pipeline...")
    e2e_cmd = [
        sys.executable,
        str(QWEN_ROOT / "run_e2e_qwen3.py"),
        "--kaggle",
        "--push-to-hub",
        "--epochs",
        str(args.epochs),
        "--save-steps",
        str(args.save_steps),
        "--seq-len",
        str(args.seq_len),
    ]
    if args.skip_train:
        e2e_cmd.append("--skip-train")
    if args.skip_merge:
        e2e_cmd.append("--skip-merge")
    if args.skip_gguf:
        e2e_cmd.append("--skip-gguf")

    subprocess.run(e2e_cmd, check=True)

    print("\n=================================================================")
    print("🎉 Kaggle Qwen3-8B Pipeline Completed Successfully!")
    print("=================================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
