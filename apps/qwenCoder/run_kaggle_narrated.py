#!/usr/bin/env python3
"""One-Click Kaggle GPU Runner for Continued SFT + DPO Manim Voiceover Pipeline.

Executes the entire end-to-end curriculum on Kaggle P100 / T4 GPUs:
1. Auto-retrieves HF_TOKEN and WANDB_API_KEY from Kaggle UserSecrets.
2. Checks PyTorch CUDA compatibility (skips redundant 2.5GB torch reinstallation).
3. Prepares aligned Continued SFT and DPO preference datasets from the 400 narrated scripts.
4. Executes Continued SFT fine-tuning and pushes the updated LoRA adapter to Hugging Face Hub.
5. Executes Direct Preference Optimization (DPO) and pushes the aligned adapter to Hugging Face Hub.
6. (Optional) Merges adapter and quantizes to GGUF (Q4_K_M & Q8_0).

Usage in Kaggle Notebook:
    !python3 apps/qwenCoder/run_kaggle_narrated.py
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

QWEN_ROOT = Path(__file__).resolve().parent
REPO_ROOT = QWEN_ROOT.parent.parent

DEFAULT_BASE_MODEL = "Qwen/Qwen3-8B"
DEFAULT_INIT_ADAPTER = "nabin2004/AOS-qwen3-8b-adapter"
DEFAULT_HUB_SFT_REPO = "nabin2004/AOS-qwen3-8b-narrated-adapter"
DEFAULT_HUB_DPO_REPO = "nabin2004/AOS-qwen3-8b-narrated-dpo"


def setup_kaggle_secrets() -> None:
    """Retrieve HF_TOKEN and WANDB_API_KEY from Kaggle UserSecretsClient if available."""
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
    """Check if CUDA matrix multiplication works."""
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
    """Install requirements in Kaggle system Python without unnecessary torch reinstallation."""
    python_exe = sys.executable

    if force_reinstall_torch or not is_cuda_working():
        print("\n==> Installing PyTorch with CUDA support (cu118 for Pascal P100)...")
        subprocess.run(
            [
                python_exe,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "torch>=2.4.0",
                "torchvision",
                "torchaudio",
                "--index-url",
                "https://download.pytorch.org/whl/cu118",
            ],
            check=True,
        )
    else:
        print("✔ Existing PyTorch installation has working CUDA. Skipping torch wheel re-download.")

    print("\n==> Installing SFT & DPO training dependencies...")
    subprocess.run(
        [
            python_exe,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "transformers>=4.51.0",
            "trl>=0.19.0",
            "peft>=0.19.1",
            "datasets>=5.0.0",
            "bitsandbytes>=0.45.0",
            "accelerate>=1.0.0",
            "huggingface-hub>=0.27.0",
        ],
        check=True,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="One-Click Kaggle Runner for Continued SFT + DPO Manim Voiceover")
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL, help=f"Base model ID (default: {DEFAULT_BASE_MODEL})")
    parser.add_argument("--init-adapter", default=DEFAULT_INIT_ADAPTER, help=f"Starting LoRA adapter (default: {DEFAULT_INIT_ADAPTER})")
    parser.add_argument("--hub-sft-repo", default=DEFAULT_HUB_SFT_REPO, help=f"HF SFT output repo (default: {DEFAULT_HUB_SFT_REPO})")
    parser.add_argument("--hub-dpo-repo", default=DEFAULT_HUB_DPO_REPO, help=f"HF DPO output repo (default: {DEFAULT_HUB_DPO_REPO})")
    parser.add_argument("--sft-epochs", type=int, default=2, help="SFT epochs (default: 2)")
    parser.add_argument("--dpo-epochs", type=int, default=1, help="DPO epochs (default: 1)")
    parser.add_argument("--sft-lr", type=float, default=5e-5, help="SFT learning rate (default: 5e-5)")
    parser.add_argument("--dpo-lr", type=float, default=5e-6, help="DPO learning rate (default: 5e-6)")
    parser.add_argument("--dpo-beta", type=float, default=0.1, help="DPO beta (default: 0.1)")
    parser.add_argument("--skip-sft", action="store_true", help="Skip Continued SFT stage")
    parser.add_argument("--skip-dpo", action="store_true", help="Skip DPO stage")
    parser.add_argument("--no-push", action="store_true", help="Do not push models to Hugging Face Hub")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    print("=================================================================")
    print("🚀 Master Kaggle Narrated Manim Pipeline (Continued SFT + DPO)")
    print(f"Base Model:     {args.base_model}")
    print(f"Starting LoRA:  {args.init_adapter}")
    print(f"Target SFT Hub: {args.hub_sft_repo}")
    print(f"Target DPO Hub: {args.hub_dpo_repo}")
    print("=================================================================")

    setup_kaggle_secrets()
    setup_environment()

    # Step 1: Prepare datasets
    print("\n[Step 1/3] Preparing Aligned SFT & DPO Datasets...")
    prep_cmd = [
        sys.executable,
        str(QWEN_ROOT / "prepare_narrated_datasets.py"),
    ]
    if not args.no_push:
        prep_cmd.append("--push-dpo")
    subprocess.run(prep_cmd, check=True)

    sft_adapter_path = QWEN_ROOT / "qwen3-8b-narrated-sft"

    # Step 2: Continued SFT
    if not args.skip_sft:
        print("\n[Step 2/3] Launching Continued SFT Fine-Tuning...")
        sft_cmd = [
            sys.executable,
            str(QWEN_ROOT / "run_narrated_sft.py"),
            "--base-model",
            args.base_model,
            "--init-adapter",
            args.init_adapter,
            "--output-dir",
            str(sft_adapter_path),
            "--hub-adapter-repo",
            args.hub_sft_repo,
            "--epochs",
            str(args.sft_epochs),
            "--lr",
            str(args.sft_lr),
        ]
        if not args.no_push and os.environ.get("HF_TOKEN"):
            sft_cmd.append("--push-to-hub")
        subprocess.run(sft_cmd, check=True)
    else:
        print("\n[Step 2/3] Skipped Continued SFT (--skip-sft set).")

    # Step 3: Direct Preference Optimization (DPO)
    if not args.skip_dpo:
        print("\n[Step 3/3] Launching Direct Preference Optimization (DPO)...")
        # If Continued SFT was just run, initialize DPO from the local newly trained adapter
        starting_dpo_adapter = (
            str(sft_adapter_path)
            if (sft_adapter_path.is_dir() and not args.skip_sft)
            else args.hub_sft_repo
        )

        dpo_cmd = [
            sys.executable,
            str(QWEN_ROOT / "run_narrated_dpo.py"),
            "--base-model",
            args.base_model,
            "--sft-adapter",
            starting_dpo_adapter,
            "--hub-dpo-repo",
            args.hub_dpo_repo,
            "--epochs",
            str(args.dpo_epochs),
            "--lr",
            str(args.dpo_lr),
            "--beta",
            str(args.dpo_beta),
        ]
        if not args.no_push and os.environ.get("HF_TOKEN"):
            dpo_cmd.append("--push-to-hub")
        subprocess.run(dpo_cmd, check=True)
    else:
        print("\n[Step 3/3] Skipped DPO (--skip-dpo set).")

    print("\n=================================================================")
    print("🎉 All Stages Completed Successfully!")
    if not args.no_push and os.environ.get("HF_TOKEN"):
        if not args.skip_sft:
            print(f"SFT Adapter Hub: https://huggingface.co/{args.hub_sft_repo}")
        if not args.skip_dpo:
            print(f"DPO Adapter Hub: https://huggingface.co/{args.hub_dpo_repo}")
    print("=================================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
