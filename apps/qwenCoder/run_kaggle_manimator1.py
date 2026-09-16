#!/usr/bin/env python3
"""Kaggle T4×2 One-Click Runner for qwen-Manimator-1 Pipeline.

Features:
  1. Auto-retrieves HF_TOKEN and WANDB_API_KEY from Kaggle UserSecretsClient.
  2. Checks PyTorch CUDA compatibility before reinstalling (saves ~2.5 GB).
  3. Installs all required SFT dependencies.
  4. Optionally uploads dataset to HF Hub (nabin2004/qwen-Manimator-1-sft-data).
  5. Launches run_manimator1.py with --kaggle-t4x2 --push-to-hub --epochs 3.

Usage in Kaggle Notebook:
    !cd /kaggle/working && git clone https://github.com/nabin2004/AOS.git 2>/dev/null || git -C /kaggle/working/AOS pull
    !python3 /kaggle/working/AOS/apps/qwenCoder/run_kaggle_manimator1.py
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

QWEN_ROOT = Path(__file__).resolve().parent
REPO_ROOT = QWEN_ROOT.parent.parent

# Dataset location inside the repo (305 validated examples)
DATASET_PATH = REPO_ROOT / "apps" / "new_data" / "train_clean.jsonl"


def setup_kaggle_secrets() -> None:
    """Retrieve HF_TOKEN and WANDB_API_KEY from Kaggle UserSecretsClient if not set."""
    for secret_key in ("HF_TOKEN", "WANDB_API_KEY"):
        if secret_key not in os.environ:
            try:
                from kaggle_secrets import UserSecretsClient  # type: ignore

                val = UserSecretsClient().get_secret(secret_key)
                if val:
                    os.environ[secret_key] = val
                    print(f"✔ Retrieved {secret_key} from Kaggle UserSecrets.")
            except Exception as exc:
                if secret_key == "HF_TOKEN":
                    print(f"Notice: Could not fetch {secret_key}: {exc}")


def is_cuda_working() -> bool:
    """Test whether system PyTorch can run a CUDA matmul."""
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
    """Install SFT dependencies; skip PyTorch reinstall if CUDA already works."""
    python_exe = sys.executable

    if not force_reinstall_torch and is_cuda_working():
        import torch

        print(
            f"✔ PyTorch {torch.__version__} + CUDA {torch.version.cuda} working. "
            "Skipping PyTorch reinstall."
        )
    else:
        print("==> Pinning PyTorch 2.7.1+cu118 for Kaggle T4 (sm_75)...")
        subprocess.run(
            [python_exe, "-m", "pip", "uninstall", "-y", "torch", "torchvision", "torchaudio"],
            check=False,
        )
        subprocess.run(
            [
                python_exe, "-m", "pip", "install",
                "torch==2.7.1", "torchvision==0.22.1", "torchaudio==2.7.1",
                "--index-url", "https://download.pytorch.org/whl/cu118",
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
        "safetensors",
        "wrapt",
    ]
    subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([python_exe, "-m", "pip", "install"] + deps, check=True)

    print("==> Installing qwenCoder package in editable mode (--no-deps)...")
    subprocess.run(
        [python_exe, "-m", "pip", "install", "-e", str(QWEN_ROOT), "--no-deps"],
        check=True,
    )


def upload_dataset_to_hub(dataset_path: Path, repo_id: str, token: str) -> None:
    """Upload the dataset JSONL to Hugging Face Hub as a dataset repository."""
    try:
        from huggingface_hub import HfApi  # type: ignore

        api = HfApi(token=token)
        print(f"\n==> Uploading dataset to https://huggingface.co/datasets/{repo_id}...")
        api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True, token=token)
        api.upload_file(
            path_or_fileobj=str(dataset_path),
            path_in_repo="train.jsonl",
            repo_id=repo_id,
            repo_type="dataset",
            token=token,
        )
        # Write a minimal README for the dataset card
        readme = f"""---
license: apache-2.0
task_categories:
  - text-generation
language:
  - en
tags:
  - manim
  - manim-voiceover
  - manimce
  - code-generation
  - sft
  - aos
pretty_name: qwen-Manimator-1 SFT Dataset
---

# qwen-Manimator-1 SFT Dataset

Training dataset for [`nabin2004/qwen-Manimator-1-sft`](https://huggingface.co/nabin2004/qwen-Manimator-1-sft).

Contains {sum(1 for _ in dataset_path.open())} chat-format JSONL examples for fine-tuning Qwen3-8B
to generate pedagogically rich ManimCE + Manim Voiceover animations.

## Format

Each row: `{{"messages": [{{"role": "system", ...}}, {{"role": "user", ...}}, {{"role": "assistant", ...}}]}}`

The `assistant` turn contains a `<Plan>` block and a fenced Python code block with:
- `VoiceoverScene`
- `AOSSpeechService`
- `<bookmark>` tags + `wait_until_bookmark` for audio sync
"""
        import io
        api.upload_file(
            path_or_fileobj=io.BytesIO(readme.encode()),
            path_in_repo="README.md",
            repo_id=repo_id,
            repo_type="dataset",
            token=token,
        )
        print(f"✔ Dataset uploaded to https://huggingface.co/datasets/{repo_id}")
    except Exception as exc:
        print(f"WARNING: Dataset upload failed: {exc}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Kaggle T4×2 One-Click Runner for qwen-Manimator-1"
    )
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--save-steps", type=int, default=200)
    parser.add_argument("--seq-len", type=int, default=4500)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument(
        "--force-reinstall-torch", action="store_true", help="Force PyTorch cu118 reinstall"
    )
    parser.add_argument(
        "--skip-upload-dataset", action="store_true", help="Skip dataset HF Hub upload"
    )
    parser.add_argument("--skip-train", action="store_true", help="Skip training step")
    parser.add_argument("--skip-merge", action="store_true", help="Skip merge step")
    parser.add_argument("--skip-gguf", action="store_true", help="Skip GGUF export step")
    parser.add_argument(
        "--no-push", action="store_true", help="Dry run: skip all HF Hub pushes"
    )
    args = parser.parse_args()

    print("=================================================================")
    print("🎨 qwen-Manimator-1 — Kaggle T4×2 One-Click Pipeline")
    print("=================================================================")

    # 1. Secrets
    setup_kaggle_secrets()

    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not hf_token:
        print(
            "WARNING: HF_TOKEN not set. HF Hub pushes will fail.\n"
            "Add HF_TOKEN to Kaggle Secrets → Add-ons → Secrets.",
            file=sys.stderr,
        )

    # 2. Environment
    setup_environment(force_reinstall_torch=args.force_reinstall_torch)

    # 3. Dataset upload
    if not args.skip_upload_dataset and hf_token and DATASET_PATH.is_file():
        upload_dataset_to_hub(
            dataset_path=DATASET_PATH,
            repo_id="nabin2004/qwen-Manimator-1-sft-data",
            token=hf_token,
        )
    else:
        if not DATASET_PATH.is_file():
            print(f"WARNING: Dataset not found at {DATASET_PATH}", file=sys.stderr)

    # 4. Launch E2E pipeline
    print("\n==> Launching qwen-Manimator-1 End-to-End Pipeline...")
    e2e_cmd = [
        sys.executable,
        str(QWEN_ROOT / "run_manimator1.py"),
        "--kaggle-t4x2",
        "--epochs", str(args.epochs),
        "--save-steps", str(args.save_steps),
        "--seq-len", str(args.seq_len),
        "--max-samples", str(args.max_samples),
    ]
    if not args.no_push and hf_token:
        e2e_cmd.append("--push-to-hub")
    if args.skip_train:
        e2e_cmd.append("--skip-train")
    if args.skip_merge:
        e2e_cmd.append("--skip-merge")
    if args.skip_gguf:
        e2e_cmd.append("--skip-gguf")

    subprocess.run(e2e_cmd, check=True)

    print("\n=================================================================")
    print("🎉 Kaggle qwen-Manimator-1 Pipeline Completed Successfully!")
    print("=================================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
