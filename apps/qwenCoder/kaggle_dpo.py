#!/usr/bin/env python3
"""One-Click Kaggle GPU Runner for Manim Voiceover DPO Training (T4 x2 / P100).

Optimized for Kaggle GPU environments:
- GPU T4 x2 (Recommended): Automatically uses 4-bit NF4 QLoRA with hardware Tensor Cores (sm_75).
- Auto-retrieves HF_TOKEN and WANDB_API_KEY from Kaggle UserSecretsClient.
- Streams the clean 361-sample preference dataset from `nabin2004/manim-narrated-dpo-400`.
- Pushes the aligned DPO LoRA adapter to Hugging Face Hub: `nabin2004/AOS-qwen3-8b-narrated-dpo`.

Usage in Kaggle Notebook (with GPU T4 x2 & Internet ON):
    !python3 apps/qwenCoder/kaggle_dpo.py
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
DEFAULT_SFT_ADAPTER = "nabin2004/AOS-qwen3-8b-narrated-adapter"
DEFAULT_HUB_DPO_REPO = "nabin2004/AOS-qwen3-8b-narrated-dpo"
DEFAULT_HF_DATASET_REPO = "nabin2004/manim-narrated-dpo-400"


def setup_kaggle_secrets() -> None:
    """Retrieve secrets from Kaggle UserSecretsClient if running on Kaggle."""
    if "HF_TOKEN" not in os.environ:
        try:
            from kaggle_secrets import UserSecretsClient  # type: ignore

            secrets = UserSecretsClient()
            token = secrets.get_secret("HF_TOKEN")
            if token:
                os.environ["HF_TOKEN"] = token
                print("✔ Successfully retrieved HF_TOKEN from Kaggle UserSecrets.")
        except Exception:
            pass

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
    """Test whether CUDA tensor operations execute properly."""
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
    """Prepare Python environment on Kaggle with stable package pins."""
    python_exe = sys.executable

    print("\n[1/3] Checking GPU and PyTorch environment...")
    if not force_reinstall_torch and is_cuda_working():
        import torch

        name = torch.cuda.get_device_name(0)
        major, minor = torch.cuda.get_device_capability(0)
        print(f"✔ Active GPU: {name} (Compute Capability {major}.{minor})")
        print("✔ PyTorch CUDA is already operational. Skipping 2.5 GB torch wheel re-download.")
    else:
        print("⚡ Ensuring PyTorch with CUDA support...")
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
                "torch==2.5.1",
                "torchvision==0.20.1",
                "torchaudio==2.5.1",
                "--index-url",
                "https://download.pytorch.org/whl/cu121",
            ],
            check=True,
        )

    print("\n[2/3] Installing/upgrading DPO alignment dependencies...")
    subprocess.run(
        [
            python_exe,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "transformers>=4.48.0,<5.0.0",
            "trl>=0.12.0,<1.0.0",
            "peft>=0.14.0",
            "datasets>=3.0.0",
            "bitsandbytes>=0.45.0",
            "accelerate>=1.0.0",
            "huggingface-hub>=0.27.0",
        ],
        check=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="One-Click Kaggle DPO Trainer for Qwen3-8B Narrated Manim"
    )
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL, help=f"Base model ID (default: {DEFAULT_BASE_MODEL})")
    parser.add_argument("--sft-adapter", default=DEFAULT_SFT_ADAPTER, help=f"SFT adapter ID (default: {DEFAULT_SFT_ADAPTER})")
    parser.add_argument("--hf-dataset", default=DEFAULT_HF_DATASET_REPO, help=f"HF dataset (default: {DEFAULT_HF_DATASET_REPO})")
    parser.add_argument("--hub-dpo-repo", default=DEFAULT_HUB_DPO_REPO, help=f"Target HF repo for DPO adapter (default: {DEFAULT_HUB_DPO_REPO})")
    parser.add_argument("--epochs", type=int, default=1, help="DPO training epochs (default: 1)")
    parser.add_argument("--lr", type=float, default=5e-6, help="Learning rate (default: 5e-6)")
    parser.add_argument("--beta", type=float, default=0.1, help="DPO beta temperature (default: 0.1)")
    parser.add_argument("--batch-size", type=int, default=1, help="Per-device batch size (default: 1)")
    parser.add_argument("--grad-accum", type=int, default=8, help="Gradient accumulation steps (default: 8)")
    parser.add_argument("--max-length", type=int, default=2048, help="Max sequence length (default: 2048)")
    parser.add_argument("--max-prompt-length", type=int, default=1024, help="Max prompt length (default: 1024)")
    parser.add_argument("--use-4bit", action="store_true", default=True, help="Use 4-bit NF4 QLoRA (default: True on sm_75+)")
    parser.add_argument("--use-8bit", action="store_true", default=False, help="Use 8-bit quantization")
    parser.add_argument("--no-push", action="store_true", help="Do not upload DPO LoRA to Hugging Face")
    parser.add_argument("--smoke", action="store_true", help="Smoke test (1 step, small dataset)")
    parser.add_argument("--force-reinstall-torch", action="store_true", help="Force reinstall PyTorch")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    print("=================================================================")
    print("🚀 One-Click Kaggle DPO Alignment Runner (Qwen3-8B Narrated)")
    print(f"Base LLM:      {args.base_model}")
    print(f"SFT Adapter:   {args.sft_adapter}")
    print(f"Dataset Hub:   {args.hf_dataset}")
    print(f"Target DPO:    {args.hub_dpo_repo}")
    print("=================================================================")

    setup_kaggle_secrets()
    setup_environment(force_reinstall_torch=args.force_reinstall_torch)

    import torch

    major = 99
    if torch.cuda.is_available():
        major, minor = torch.cuda.get_device_capability(0)
        device_name = torch.cuda.get_device_name(0)
        print(f"\n✔ Target GPU: {device_name} (Compute Capability: {major}.{minor})")

    # Detect Pascal P100 limitation
    if major < 7:
        print("\n" + "=" * 65)
        print("⚠️  NOTICE: Tesla P100 (sm_60) detected!")
        print("NVIDIA Pascal GPUs lack Tensor Cores. As a result, bitsandbytes")
        print("cuBLASLt INT8/FP4 matrix operations will fail with status 15.")
        print("\n👉 HIGHLY RECOMMENDED FIX:")
        print("   Switch your Kaggle Accelerator to 'GPU T4 x2' (or 'GPU T4').")
        print("   In Kaggle: Notebook settings (right panel) -> Accelerator -> 'GPU T4 x2'.")
        print("   Tesla T4 has Turing Tensor Cores (sm_75) and runs 4-bit NF4 QLoRA flawlessly.")
        print("=" * 65 + "\n")

    output_adapter_dir = QWEN_ROOT / "qwen3-8b-narrated-dpo"

    print("\n[3/3] Launching DPO Training via run_narrated_dpo.py...")
    dpo_cmd = [
        sys.executable,
        str(QWEN_ROOT / "run_narrated_dpo.py"),
        "--base-model",
        args.base_model,
        "--sft-adapter",
        args.sft_adapter,
        "--hf-dataset-repo",
        args.hf_dataset,
        "--output-dir",
        str(output_adapter_dir),
        "--hub-dpo-repo",
        args.hub_dpo_repo,
        "--epochs",
        str(args.epochs),
        "--lr",
        str(args.lr),
        "--beta",
        str(args.beta),
        "--batch-size",
        str(args.batch_size),
        "--grad-accum",
        str(args.grad_accum),
        "--max-length",
        str(args.max_length),
        "--max-prompt-length",
        str(args.max_prompt_length),
    ]

    if args.use_8bit:
        dpo_cmd.append("--use-8bit")
    else:
        dpo_cmd.append("--use-4bit")

    if not args.no_push and os.environ.get("HF_TOKEN"):
        dpo_cmd.append("--push-to-hub")

    if args.smoke:
        dpo_cmd.append("--smoke")

    res = subprocess.run(dpo_cmd)
    if res.returncode != 0:
        print(f"\n❌ DPO training exited with error code {res.returncode}", file=sys.stderr)
        return res.returncode

    print("\n=================================================================")
    print("🎉 DPO Training and Alignment Finished Successfully!")
    if not args.no_push and os.environ.get("HF_TOKEN"):
        print(f"DPO LoRA Adapter on Hub: https://huggingface.co/{args.hub_dpo_repo}")
    print("=================================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
